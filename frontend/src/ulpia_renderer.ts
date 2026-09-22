/**
 * ULPIA HIGH-PERFORMANCE WEBGL2 RENDERER
 * Project: Traianus — Spatial Control Plane
 *
 * Zero-Copy binary resting buffer (64 B/node) + separate transition VBO for
 * the 3-Point Parabolic Corrector. GPU-side OKLCH -> sRGB conversion.
 *
 * Binary contract (matches traianus/geometry/zero_copy.py):
 *   offset  0-11  x, y, z            (3 x float32)
 *   offset 12-23  L, C, H            (3 x float32, channels normalized [0,1])
 *   offset 24-55  note_id            (32-byte UUID hex, CPU-side only)
 *   offset 56-63  padding            (8-byte alignment)
 *   total                             64 bytes
 *
 * Transition buffer (separate VBO, only bound during animation):
 *   per node: a_start_pos, a_end_pos, a_mid_deviation (3 x vec3)
 *
 * Lifecycle buffer (separate VBO, one byte per node, outside the 64 B block):
 *   the slot of the node's lifecycle mark (see lifecycle.ts), drawn as a ring outside the body.
 *
 * WebGL2 correctness notes (review findings):
 *   - Uses gl.PROGRAM_POINT_SIZE (WebGL2), NOT the desktop VERTEX_PROGRAM_POINT_SIZE.
 *   - Resting attributes (0,1) read the 64 B VBO; transition attributes (2,3,4)
 *     stay unbound-to-zero when u_interpolationTime is idle, so the resting
 *     position is used.
 *   - Channels are normalized [0,1] consistently with the exporter and the
 *     fragment shader expectations.
 */

import { MARK_SLOTS, markTables } from "./lifecycle";

const VERTEX_SHADER_SOURCE = `#version 300 es
layout(location = 0) in vec3 a_position;       // Resting position (xyz from 64B block)
layout(location = 1) in vec3 a_lch;            // Chromatic channel (L, C, H in [0,1])
layout(location = 2) in vec3 a_start_pos;      // Parabolic start P_ini
layout(location = 3) in vec3 a_end_pos;        // Parabolic end   P_fin
layout(location = 4) in vec3 a_mid_deviation;  // D_mid = P_mid - (P_ini + P_fin)/2
layout(location = 5) in float a_mark;          // Lifecycle mark slot, 0 for none

uniform mat4 u_projectionMatrix;
uniform mat4 u_viewMatrix;
uniform float u_interpolationTime;   // t in [0.0, 1.0]
uniform float u_escapeVibration;     // 0..1 intensity from escape Z-score
uniform float u_pointScale;          // device pixels per CSS pixel
uniform int u_anchor;                // Index of the anchor node, -1 for none
uniform vec4 u_markColor[${MARK_SLOTS}];   // rgba of each mark slot
uniform float u_markRing[${MARK_SLOTS}];   // ring width of each mark slot, CSS pixels

out vec3 v_lch;
out float v_vibration_offset;
out float v_anchor;
out vec4 v_ring;
out float v_body;

float hash(float n) { return fract(sin(n) * 43758.5453123); }

void main() {
    vec3 base_pos = a_position;

    // 3-Point Parabolic Corrector: P(t) = (1-t)*P_ini + t*P_fin + 4t(1-t)*D_mid.
    // ONLY active for a strictly-open transition; at t=0 or t=1 the resting
    // position is used so the resting/transition buffers never mix.
    if (u_interpolationTime > 0.0 && u_interpolationTime < 1.0) {
        float t = u_interpolationTime;
        vec3 linear_path = (1.0 - t) * a_start_pos + t * a_end_pos;
        vec3 parabolic_correction = 4.0 * t * (1.0 - t) * a_mid_deviation;
        base_pos = linear_path + parabolic_correction;
    }

    // Escape vibration: pseudo-random jitter proportional to the semantic
    // escape Z-score (visual feedback before the Schmitt Trigger recalibrates).
    if (u_escapeVibration > 0.0) {
        float noise = hash(dot(base_pos, vec3(12.9898, 78.233, 45.164)));
        base_pos.xy += (noise - 0.5) * u_escapeVibration * 0.05;
    }

    gl_Position = u_projectionMatrix * u_viewMatrix * vec4(base_pos, 1.0);

    // Node size scales with Luminance (density in [0,1]); the anchor is drawn larger.
    // The lifecycle ring lies outside that body, so the body keeps its size.
    float is_anchor = gl_VertexID == u_anchor ? 1.0 : 0.0;
    int slot = int(a_mark + 0.5);
    float body = clamp(a_lch.x * 12.0, 4.0, 32.0) * (1.0 + 1.5 * is_anchor);
    float ring = 2.0 * u_markRing[slot];
    gl_PointSize = (body + ring) * u_pointScale;

    v_lch = a_lch;
    v_vibration_offset = u_escapeVibration;
    v_anchor = is_anchor;
    v_ring = u_markColor[slot];
    v_body = body / (body + ring);
}
`;

const FRAGMENT_SHADER_SOURCE = `#version 300 es
precision highp float;

in vec3 v_lch;
in float v_vibration_offset;
in float v_anchor;
in vec4 v_ring;
in float v_body;
out vec4 outColor;

#define PI 3.141592653589793

// Stands for "no valid candidate" where the C++ reference below uses FLT_MAX:
// any value far above the realistic magnitude of t (order 1 here) selects the
// same branch in the min() that follows.
const float GAMUT_T_SENTINEL = 1.0e30;

// Defined at (2) below; declared here because the gamut search calls it.
vec3 oklab_to_linear_srgb(vec3 lab);

// 0. sRGB gamut boundary in OKLab (Bjoern Ottosson reference implementation,
//    MIT: https://bottosson.github.io/posts/gamutclipping/, "Intersection with
//    sRGB gamut"). Ported as published; the substitutions are GLSL-only (vec2
//    for the LC pair, cbrt_safe for cbrtf, GAMUT_T_SENTINEL for FLT_MAX,
//    bc/bc1/bc2 for the block-shadowed b/b1/b2).

// GLSL pow(x, y) is undefined for negative x, so the cube root is taken on the
// magnitude and the sign restored.
float cbrt_safe(float x) {
    return sign(x) * pow(abs(x), 1.0 / 3.0);
}

// Maximum saturation S = C/L along the hue direction (a, b), with a^2 + b^2 = 1:
// a polynomial approximation refined by one step of Halley's method.
float compute_max_saturation(float a, float b) {
    float k0, k1, k2, k3, k4, wl, wm, ws;

    if (-1.88170328 * a - 0.80936493 * b > 1.0) {
        // Red component.
        k0 = 1.19086277; k1 = 1.76576728; k2 = 0.59662641; k3 = 0.75515197; k4 = 0.56771245;
        wl = 4.0767416621; wm = -3.3077115913; ws = 0.2309699292;
    } else if (1.81444104 * a - 1.19445276 * b > 1.0) {
        // Green component.
        k0 = 0.73956515; k1 = -0.45954404; k2 = 0.08285427; k3 = 0.12541070; k4 = 0.14503204;
        wl = -1.2684380046; wm = 2.6097574011; ws = -0.3413193965;
    } else {
        // Blue component.
        k0 = 1.35733652; k1 = -0.00915799; k2 = -1.15130210; k3 = -0.50559606; k4 = 0.00692167;
        wl = -0.0041960863; wm = -0.7034186147; ws = 1.7076147010;
    }

    float S = k0 + k1 * a + k2 * b + k3 * a * a + k4 * a * b;

    float k_l = 0.3963377774 * a + 0.2158037573 * b;
    float k_m = -0.1055613458 * a - 0.0638541728 * b;
    float k_s = -0.0894841775 * a - 1.2914855480 * b;

    {
        float l_ = 1.0 + S * k_l;
        float m_ = 1.0 + S * k_m;
        float s_ = 1.0 + S * k_s;

        float l = l_ * l_ * l_;
        float m = m_ * m_ * m_;
        float s = s_ * s_ * s_;

        float l_dS = 3.0 * k_l * l_ * l_;
        float m_dS = 3.0 * k_m * m_ * m_;
        float s_dS = 3.0 * k_s * s_ * s_;

        float l_dS2 = 6.0 * k_l * k_l * l_;
        float m_dS2 = 6.0 * k_m * k_m * m_;
        float s_dS2 = 6.0 * k_s * k_s * s_;

        float f = wl * l + wm * m + ws * s;
        float f1 = wl * l_dS + wm * m_dS + ws * s_dS;
        float f2 = wl * l_dS2 + wm * m_dS2 + ws * s_dS2;

        S = S - f * f1 / (f1 * f1 - 0.5 * f * f2);
    }

    return S;
}

// Cusp of the sRGB gamut along the hue direction (a, b), as vec2(L_cusp, C_cusp).
vec2 find_cusp(float a, float b) {
    float S_cusp = compute_max_saturation(a, b);

    vec3 rgb_at_max = oklab_to_linear_srgb(vec3(1.0, S_cusp * a, S_cusp * b));
    float L_cusp = cbrt_safe(1.0 / max(max(rgb_at_max.x, rgb_at_max.y), rgb_at_max.z));
    float C_cusp = L_cusp * S_cusp;

    return vec2(L_cusp, C_cusp);
}

// Parameter t at which the segment from (L0, 0) to (L1, C1) leaves the sRGB
// gamut, so the boundary point is L = L0*(1-t) + t*L1, C = t*C1.
float find_gamut_intersection(float a, float b, float L1, float C1, float L0) {
    vec2 cusp = find_cusp(a, b);

    float t;
    if (((L1 - L0) * cusp.y - (cusp.x - L0) * C1) <= 0.0) {
        // Lower half.
        t = cusp.y * L0 / (C1 * cusp.x + cusp.y * (L0 - L1));
    } else {
        // Upper half: first an approximation, then one step of Halley's method.
        t = cusp.y * (L0 - 1.0) / (C1 * (cusp.x - 1.0) + cusp.y * (L0 - L1));

        {
            float dL = L1 - L0;
            float dC = C1;

            float k_l = 0.3963377774 * a + 0.2158037573 * b;
            float k_m = -0.1055613458 * a - 0.0638541728 * b;
            float k_s = -0.0894841775 * a - 1.2914855480 * b;

            float l_dt = dL + dC * k_l;
            float m_dt = dL + dC * k_m;
            float s_dt = dL + dC * k_s;

            {
                float L = L0 * (1.0 - t) + t * L1;
                float C = t * C1;

                float l_ = L + C * k_l;
                float m_ = L + C * k_m;
                float s_ = L + C * k_s;

                float l = l_ * l_ * l_;
                float m = m_ * m_ * m_;
                float s = s_ * s_ * s_;

                float ldt = 3.0 * l_dt * l_ * l_;
                float mdt = 3.0 * m_dt * m_ * m_;
                float sdt = 3.0 * s_dt * s_ * s_;

                float ldt2 = 6.0 * l_dt * l_dt * l_;
                float mdt2 = 6.0 * m_dt * m_dt * m_;
                float sdt2 = 6.0 * s_dt * s_dt * s_;

                float r = 4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s - 1.0;
                float r1 = 4.0767416621 * ldt - 3.3077115913 * mdt + 0.2309699292 * sdt;
                float r2 = 4.0767416621 * ldt2 - 3.3077115913 * mdt2 + 0.2309699292 * sdt2;

                float u_r = r1 / (r1 * r1 - 0.5 * r * r2);
                float t_r = -r * u_r;

                float g = -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s - 1.0;
                float g1 = -1.2684380046 * ldt + 2.6097574011 * mdt - 0.3413193965 * sdt;
                float g2 = -1.2684380046 * ldt2 + 2.6097574011 * mdt2 - 0.3413193965 * sdt2;

                float u_g = g1 / (g1 * g1 - 0.5 * g * g2);
                float t_g = -g * u_g;

                float bc = -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s - 1.0;
                float bc1 = -0.0041960863 * ldt - 0.7034186147 * mdt + 1.7076147010 * sdt;
                float bc2 = -0.0041960863 * ldt2 - 0.7034186147 * mdt2 + 1.7076147010 * sdt2;

                float u_b = bc1 / (bc1 * bc1 - 0.5 * bc * bc2);
                float t_b = -bc * u_b;

                t_r = u_r >= 0.0 ? t_r : GAMUT_T_SENTINEL;
                t_g = u_g >= 0.0 ? t_g : GAMUT_T_SENTINEL;
                t_b = u_b >= 0.0 ? t_b : GAMUT_T_SENTINEL;

                t += min(t_r, min(t_g, t_b));
            }
        }
    }

    return t;
}

// 1. OKLCH -> OKLab (channels normalized [0,1]; L used as-is, C taken as the
//    fraction lch.y of C_max: the chroma at which the sRGB gamut ends for this
//    pixel's own lightness and hue. Since the search line has C1 = 1.0 and
//    L1 == L0 == L, the returned t is that maximum chroma directly. References:
//    https://bottosson.github.io/posts/oklab/ and
//    https://bottosson.github.io/posts/gamutclipping/).
vec3 oklch_to_oklab(vec3 lch) {
    float L = lch.x;
    float h_rad = lch.z * 2.0 * PI;
    float a_dir = cos(h_rad);
    float b_dir = sin(h_rad);
    float C_max = find_gamut_intersection(a_dir, b_dir, L, 1.0, L);
    float C = lch.y * C_max;
    return vec3(L, C * cos(h_rad), C * sin(h_rad));
}

// 2. OKLab -> linear sRGB (Bjoern Ottosson reference constants:
//    https://bottosson.github.io/posts/oklab/, "Converting from OKLab to sRGB").
vec3 oklab_to_linear_srgb(vec3 lab) {
    float l_ = lab.x + 0.3963377774 * lab.y + 0.2158037573 * lab.z;
    float m_ = lab.x - 0.1055613458 * lab.y - 0.0638541728 * lab.z;
    float s_ = lab.x - 0.0894841775 * lab.y - 1.2914855480 * lab.z;

    float l = l_ * l_ * l_;
    float m = m_ * m_ * m_;
    float s = s_ * s_ * s_;

    return vec3(
        +4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
        -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
        -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s
    );
}

float srgb_gamma(float c) {
    if (c <= 0.0031308) {
        return 12.92 * c;
    } else {
        return 1.055 * pow(c, 1.0 / 2.4) - 0.055;
    }
}

// 3. linear sRGB -> sRGB (gamma encoding, clamped).
vec3 linear_srgb_to_srgb(vec3 rgb_linear) {
    return clamp(vec3(srgb_gamma(rgb_linear.x), srgb_gamma(rgb_linear.y), srgb_gamma(rgb_linear.z)), 0.0, 1.0);
}

void main() {
    // Perfectly circular point with hardware antialiasing.
    vec2 circ_coord = 2.0 * gl_PointCoord - 1.0;
    float dist = dot(circ_coord, circ_coord);
    if (dist > 1.0) {
        discard;
    }
    float alpha = smoothstep(1.0, 0.8, dist);

    vec3 oklab = oklch_to_oklab(v_lch);
    vec3 linear_srgb = oklab_to_linear_srgb(oklab);
    vec3 srgb = linear_srgb_to_srgb(linear_srgb);

    // Subtle warning tint on the rim while escaping.
    if (v_vibration_offset > 0.0) {
        srgb = mix(srgb, vec3(1.0, 0.2, 0.2), v_vibration_offset * dist * 0.5);
    }

    // Squared radius within the body: the lifecycle ring lies beyond 1.0, and the body is drawn
    // as it is without a ring (v_body is 1.0).
    float body_dist = dist / (v_body * v_body);

    // The anchor keeps its colour inside a white rim.
    if (v_anchor > 0.5 && body_dist > 0.55) {
        srgb = vec3(1.0);
    }

    if (v_body < 1.0) {
        float on_body = 1.0 - smoothstep(0.8, 1.0, body_dist);
        srgb = mix(v_ring.rgb, srgb, on_body);
        alpha *= mix(v_ring.a, 1.0, on_body);
    }

    outColor = vec4(srgb, alpha);
}
`;

/** One resting node block is exactly 64 bytes. */
export const ULPIABLOCK_BYTES = 64;
/** Attribute 0/1 read this stride from the resting VBO. */
const RESTING_STRIDE = ULPIABLOCK_BYTES;
/** Parabolic transition: 9 contiguous floats per node. */
const TRANSITION_STRIDE = 9 * 4;
/** Attribute location of the lifecycle buffer: one byte per node. */
const MARK_ATTRIBUTE = 5;
/**
 * WebGL2 PROGRAM_POINT_SIZE capability (0x8642). Not present in the TS DOM
 * lib; gl_PointSize from the shader is honored only once this is enabled.
 */
const PROGRAM_POINT_SIZE = 0x8642;

export class UlpiaRenderer {
  private canvas: HTMLCanvasElement;
  private gl: WebGL2RenderingContext;
  private program: WebGLProgram | null = null;
  private restingVbo: WebGLBuffer | null = null;
  private transitionVbo: WebGLBuffer | null = null;
  private markVbo: WebGLBuffer | null = null;
  private vao: WebGLVertexArrayObject | null = null;
  private anchorIndex = -1;

  private viewMatrix: Float32Array = new Float32Array([
    1, 0, 0, 0,
    0, 1, 0, 0,
    0, 0, 1, 0,
    0, 0, 0, 1,
  ]);
  private projectionMatrix: Float32Array = new Float32Array([
    1, 0, 0, 0,
    0, 1, 0, 0,
    0, 0, 1, 0,
    0, 0, 0, 1,
  ]);

  constructor(canvas: HTMLCanvasElement) {
    const glContext = canvas.getContext("webgl2", {
      antialias: true,
      alpha: true,
      premultipliedAlpha: false,
    });
    if (!glContext) {
      throw new Error("WebGL 2.0 is not available in this browser.");
    }
    this.canvas = canvas;
    this.gl = glContext;
    this.initializePipeline();
  }

  private compileShader(type: number, source: string): WebGLShader {
    const gl = this.gl;
    const shader = gl.createShader(type);
    if (!shader) throw new Error("Failed to create shader.");
    gl.shaderSource(shader, source);
    gl.compileShader(shader);
    if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
      const info = gl.getShaderInfoLog(shader);
      gl.deleteShader(shader);
      throw new Error(
        `Shader compile error: ${info} (${type === gl.VERTEX_SHADER ? "vertex" : "fragment"})`
      );
    }
    return shader;
  }

  /** Compile + link the pipeline and create resting/transition VBOs + VAO. */
  private initializePipeline() {
    const gl = this.gl;
    const vertexShader = this.compileShader(gl.VERTEX_SHADER, VERTEX_SHADER_SOURCE);
    const fragmentShader = this.compileShader(gl.FRAGMENT_SHADER, FRAGMENT_SHADER_SOURCE);

    const program = gl.createProgram();
    if (!program) throw new Error("Failed to create WebGL program.");
    gl.attachShader(program, vertexShader);
    gl.attachShader(program, fragmentShader);
    gl.linkProgram(program);
    if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
      const info = gl.getProgramInfoLog(program);
      gl.deleteProgram(program);
      throw new Error(`Shader link error: ${info}`);
    }
    this.program = program;

    // WebGL2 size-from-shader requires PROGRAM_POINT_SIZE (not the desktop
    // VERTEX_PROGRAM_POINT_SIZE constant, which is INVALID_ENUM in WebGL).
    gl.enable(PROGRAM_POINT_SIZE);
    gl.enable(gl.BLEND);
    gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);

    const marks = markTables();
    gl.useProgram(program);
    gl.uniform4fv(gl.getUniformLocation(program, "u_markColor"), marks.colors);
    gl.uniform1fv(gl.getUniformLocation(program, "u_markRing"), marks.rings);

    this.restingVbo = gl.createBuffer();
    this.transitionVbo = gl.createBuffer();
    this.markVbo = gl.createBuffer();
    this.vao = gl.createVertexArray();

    // Configure the static attribute layout in the VAO.
    gl.bindVertexArray(this.vao);

    // Resting attributes: location 0 (position) and 1 (LCh) from the 64B VBO.
    gl.bindBuffer(gl.ARRAY_BUFFER, this.restingVbo);
    gl.vertexAttribPointer(0, 3, gl.FLOAT, false, RESTING_STRIDE, 0);
    gl.enableVertexAttribArray(0);
    gl.vertexAttribPointer(1, 3, gl.FLOAT, false, RESTING_STRIDE, 12);
    gl.enableVertexAttribArray(1);

    // Transition attributes: locations 2/3/4 from the separate transition VBO. They stay
    // disabled (constant zero) until a transition buffer is uploaded: drawing with them enabled
    // over an empty buffer is GL_INVALID_OPERATION and draws nothing.
    gl.bindBuffer(gl.ARRAY_BUFFER, this.transitionVbo);
    gl.vertexAttribPointer(2, 3, gl.FLOAT, false, TRANSITION_STRIDE, 0);
    gl.vertexAttribPointer(3, 3, gl.FLOAT, false, TRANSITION_STRIDE, 12);
    gl.vertexAttribPointer(4, 3, gl.FLOAT, false, TRANSITION_STRIDE, 24);

    // Lifecycle attribute: disabled (constant zero, no mark) until a lifecycle buffer is uploaded.
    gl.bindBuffer(gl.ARRAY_BUFFER, this.markVbo);
    gl.vertexAttribPointer(MARK_ATTRIBUTE, 1, gl.UNSIGNED_BYTE, false, 0, 0);

    gl.bindVertexArray(null);
    gl.bindBuffer(gl.ARRAY_BUFFER, null);
  }

  /**
   * Upload the resting ArrayBuffer (64 B per node) directly to GPU memory.
   * No JSON parsing, no per-node object instantiation — zero-copy path.
   */
  public uploadRestingBuffer(arrayBuffer: ArrayBuffer) {
    const gl = this.gl;
    if (!this.restingVbo) return;
    gl.bindBuffer(gl.ARRAY_BUFFER, this.restingVbo);
    gl.bufferData(gl.ARRAY_BUFFER, arrayBuffer, gl.STATIC_DRAW);
    gl.bindBuffer(gl.ARRAY_BUFFER, null);
  }

  /**
   * Upload one lifecycle slot per node of the resting buffer (see lifecycle.ts). It must hold at
   * least as many bytes as the resting buffer has nodes: a shorter one draws nothing.
   */
  public uploadLifecycle(marks: Uint8Array) {
    const gl = this.gl;
    if (!this.markVbo) return;
    gl.bindBuffer(gl.ARRAY_BUFFER, this.markVbo);
    gl.bufferData(gl.ARRAY_BUFFER, marks, gl.STATIC_DRAW);
    gl.bindBuffer(gl.ARRAY_BUFFER, null);
    gl.bindVertexArray(this.vao);
    gl.enableVertexAttribArray(MARK_ATTRIBUTE);
    gl.bindVertexArray(null);
  }

  /**
   * Upload an optional transition buffer (3 x vec3 per node) into the
   * separate VBO. Only meaningful while a parabolic animation is active.
   */
  public uploadTransitionBuffer(arrayBuffer: ArrayBuffer) {
    const gl = this.gl;
    if (!this.transitionVbo) return;
    gl.bindBuffer(gl.ARRAY_BUFFER, this.transitionVbo);
    gl.bufferData(gl.ARRAY_BUFFER, arrayBuffer, gl.STREAM_DRAW);
    gl.bindBuffer(gl.ARRAY_BUFFER, null);
    gl.bindVertexArray(this.vao);
    for (const location of [2, 3, 4]) gl.enableVertexAttribArray(location);
    gl.bindVertexArray(null);
  }

  /** Render one frame. */
  public renderFrame(
    totalNodes: number,
    interpolationTime = 0.0,
    escapeVibration = 0.0
  ) {
    const gl = this.gl;
    const program = this.program;
    const vao = this.vao;
    if (!program || !vao) return;

    // The drawing buffer follows the canvas's CSS size at device resolution; left alone it
    // stays at the 300x150 default and a zoom would only magnify pixels.
    const pixelRatio = window.devicePixelRatio || 1;
    const width = Math.max(1, Math.round(this.canvas.clientWidth * pixelRatio));
    const height = Math.max(1, Math.round(this.canvas.clientHeight * pixelRatio));
    if (this.canvas.width !== width || this.canvas.height !== height) {
      this.canvas.width = width;
      this.canvas.height = height;
    }
    gl.viewport(0, 0, width, height);

    gl.clearColor(0.04, 0.04, 0.05, 1.0);
    gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);

    gl.useProgram(program);
    const uProjection = gl.getUniformLocation(program, "u_projectionMatrix");
    const uView = gl.getUniformLocation(program, "u_viewMatrix");
    const uTime = gl.getUniformLocation(program, "u_interpolationTime");
    const uVibe = gl.getUniformLocation(program, "u_escapeVibration");
    const uScale = gl.getUniformLocation(program, "u_pointScale");
    const uAnchor = gl.getUniformLocation(program, "u_anchor");

    gl.uniformMatrix4fv(uProjection, false, this.projectionMatrix);
    gl.uniformMatrix4fv(uView, false, this.viewMatrix);
    gl.uniform1f(uTime, interpolationTime);
    gl.uniform1f(uVibe, escapeVibration);
    gl.uniform1f(uScale, pixelRatio);
    gl.uniform1i(uAnchor, this.anchorIndex);

    gl.bindVertexArray(vao);
    gl.drawArrays(gl.POINTS, 0, totalNodes);
    // Drawn again so that no other node covers the anchor.
    if (this.anchorIndex >= 0 && this.anchorIndex < totalNodes) {
      gl.drawArrays(gl.POINTS, this.anchorIndex, 1);
    }
    gl.bindVertexArray(null);
  }

  /** Mark node `index` of the resting buffer as the anchor; -1 for none. */
  public setAnchor(index: number) {
    this.anchorIndex = index;
  }

  public updateCamera(projection: Float32Array, view: Float32Array) {
    this.projectionMatrix.set(projection);
    this.viewMatrix.set(view);
  }
}