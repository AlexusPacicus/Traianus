/**
 * ULPIA HIGH-PERFORMANCE WEBGL2 RENDERER
 * Project: Traianus — Spatial Control Plane
 *
 * Zero-Copy binary resting buffer (64 B/node) + separate transition VBO for
 * the 3-Point Parabolic Corrector. GPU-side CIE LCh -> sRGB conversion.
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
 * WebGL2 correctness notes (review findings):
 *   - Uses gl.PROGRAM_POINT_SIZE (WebGL2), NOT the desktop VERTEX_PROGRAM_POINT_SIZE.
 *   - Resting attributes (0,1) read the 64 B VBO; transition attributes (2,3,4)
 *     stay unbound-to-zero when u_interpolationTime is idle, so the resting
 *     position is used.
 *   - Channels are normalized [0,1] consistently with the exporter and the
 *     fragment shader expectations.
 */

const VERTEX_SHADER_SOURCE = `#version 300 es
layout(location = 0) in vec3 a_position;       // Resting position (xyz from 64B block)
layout(location = 1) in vec3 a_lch;            // Chromatic channel (L, C, H in [0,1])
layout(location = 2) in vec3 a_start_pos;      // Parabolic start P_ini
layout(location = 3) in vec3 a_end_pos;        // Parabolic end   P_fin
layout(location = 4) in vec3 a_mid_deviation;  // D_mid = P_mid - (P_ini + P_fin)/2

uniform mat4 u_projectionMatrix;
uniform mat4 u_viewMatrix;
uniform float u_interpolationTime;   // t in [0.0, 1.0]
uniform float u_escapeVibration;     // 0..1 intensity from escape Z-score

out vec3 v_lch;
out float v_vibration_offset;

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

    // Node size scales with Luminance (density in [0,1]).
    gl_PointSize = clamp(a_lch.x * 12.0, 4.0, 32.0);

    v_lch = a_lch;
    v_vibration_offset = u_escapeVibration;
}
`;

const FRAGMENT_SHADER_SOURCE = `#version 300 es
precision highp float;

in vec3 v_lch;
in float v_vibration_offset;
out vec4 outColor;

#define PI 3.141592653589793

// 1. CIE LCh -> CIE Lab (channels normalized [0,1]).
vec3 lch_to_lab(vec3 lch) {
    float L = lch.x * 100.0;
    float C = lch.y * 100.0;
    float h_rad = lch.z * 2.0 * PI;
    return vec3(L, C * cos(h_rad), C * sin(h_rad));
}

float lab_f_inverse(float t) {
    float delta = 6.0 / 29.0;
    if (t > delta) {
        return t * t * t;
    } else {
        return 3.0 * delta * delta * (t - 4.0 / 29.0);
    }
}

// 2. CIE Lab -> CIE XYZ (D65 standard illuminant).
vec3 lab_to_xyz(vec3 lab) {
    float y_val = (lab.x + 16.0) / 116.0;
    float x_val = y_val + (lab.y / 500.0);
    float z_val = y_val - (lab.z / 200.0);
    return vec3(
        0.950489 * lab_f_inverse(x_val),
        1.000000 * lab_f_inverse(y_val),
        1.088840 * lab_f_inverse(z_val)
    );
}

float srgb_gamma(float c) {
    if (c <= 0.0031308) {
        return 12.92 * c;
    } else {
        return 1.055 * pow(c, 1.0 / 2.4) - 0.055;
    }
}

// 3. CIE XYZ -> sRGB (standard matrix + gamma, clamped).
vec3 xyz_to_srgb(vec3 xyz) {
    vec3 rgb_linear = vec3(
        xyz.x *  3.2406 + xyz.y * -1.5372 + xyz.z * -0.4986,
        xyz.x * -0.9689 + xyz.y *  1.8758 + xyz.z *  0.0415,
        xyz.x *  0.0557 + xyz.y * -0.2040 + xyz.z *  1.0570
    );
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

    vec3 lab = lch_to_lab(v_lch);
    vec3 xyz = lab_to_xyz(lab);
    vec3 srgb = xyz_to_srgb(xyz);

    // Subtle warning tint on the rim while escaping.
    if (v_vibration_offset > 0.0) {
        srgb = mix(srgb, vec3(1.0, 0.2, 0.2), v_vibration_offset * dist * 0.5);
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
/**
 * WebGL2 PROGRAM_POINT_SIZE capability (0x8642). Not present in the TS DOM
 * lib; gl_PointSize from the shader is honored only once this is enabled.
 */
const PROGRAM_POINT_SIZE = 0x8642;

export class UlpiaRenderer {
  private gl: WebGL2RenderingContext;
  private program: WebGLProgram | null = null;
  private restingVbo: WebGLBuffer | null = null;
  private transitionVbo: WebGLBuffer | null = null;
  private vao: WebGLVertexArrayObject | null = null;

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

    this.restingVbo = gl.createBuffer();
    this.transitionVbo = gl.createBuffer();
    this.vao = gl.createVertexArray();

    // Configure the static attribute layout in the VAO.
    gl.bindVertexArray(this.vao);

    // Resting attributes: location 0 (position) and 1 (LCh) from the 64B VBO.
    gl.bindBuffer(gl.ARRAY_BUFFER, this.restingVbo);
    gl.vertexAttribPointer(0, 3, gl.FLOAT, false, RESTING_STRIDE, 0);
    gl.enableVertexAttribArray(0);
    gl.vertexAttribPointer(1, 3, gl.FLOAT, false, RESTING_STRIDE, 12);
    gl.enableVertexAttribArray(1);

    // Transition attributes: locations 2/3/4 from the separate transition VBO.
    gl.bindBuffer(gl.ARRAY_BUFFER, this.transitionVbo);
    gl.vertexAttribPointer(2, 3, gl.FLOAT, false, TRANSITION_STRIDE, 0);
    gl.enableVertexAttribArray(2);
    gl.vertexAttribPointer(3, 3, gl.FLOAT, false, TRANSITION_STRIDE, 12);
    gl.enableVertexAttribArray(3);
    gl.vertexAttribPointer(4, 3, gl.FLOAT, false, TRANSITION_STRIDE, 24);
    gl.enableVertexAttribArray(4);

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
   * Upload an optional transition buffer (3 x vec3 per node) into the
   * separate VBO. Only meaningful while a parabolic animation is active.
   */
  public uploadTransitionBuffer(arrayBuffer: ArrayBuffer) {
    const gl = this.gl;
    if (!this.transitionVbo) return;
    gl.bindBuffer(gl.ARRAY_BUFFER, this.transitionVbo);
    gl.bufferData(gl.ARRAY_BUFFER, arrayBuffer, gl.STREAM_DRAW);
    gl.bindBuffer(gl.ARRAY_BUFFER, null);
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

    gl.clearColor(0.04, 0.04, 0.05, 1.0);
    gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);

    gl.useProgram(program);
    const uProjection = gl.getUniformLocation(program, "u_projectionMatrix");
    const uView = gl.getUniformLocation(program, "u_viewMatrix");
    const uTime = gl.getUniformLocation(program, "u_interpolationTime");
    const uVibe = gl.getUniformLocation(program, "u_escapeVibration");

    gl.uniformMatrix4fv(uProjection, false, this.projectionMatrix);
    gl.uniformMatrix4fv(uView, false, this.viewMatrix);
    gl.uniform1f(uTime, interpolationTime);
    gl.uniform1f(uVibe, escapeVibration);

    gl.bindVertexArray(vao);
    gl.drawArrays(gl.POINTS, 0, totalNodes);
    gl.bindVertexArray(null);
  }

  public updateCamera(projection: Float32Array, view: Float32Array) {
    this.projectionMatrix.set(projection);
    this.viewMatrix.set(view);
  }
}