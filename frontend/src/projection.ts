/**
 * Ulpia 5D Projection — TypeScript port of observables.py
 *
 * Pure mathematical functions for SVD-based dimensionality reduction
 * and chromatic channel mapping. Runs in the browser.
 */

// --- Linear algebra helpers ---

function transpose(M: number[][]): number[][] {
  const rows = M.length;
  const cols = M[0].length;
  const T: number[][] = Array.from({ length: cols }, () => new Array(rows));
  for (let i = 0; i < rows; i++)
    for (let j = 0; j < cols; j++) T[j][i] = M[i][j];
  return T;
}

function matMul(A: number[][], B: number[][]): number[][] {
  const m = A.length;
  const n = B[0].length;
  const k = B.length;
  const C: number[][] = Array.from({ length: m }, () => new Array(n).fill(0));
  for (let i = 0; i < m; i++)
    for (let j = 0; j < n; j++)
      for (let p = 0; p < k; p++) C[i][j] += A[i][p] * B[p][j];
  return C;
}

function meanColumns(M: number[][]): number[] {
  const n = M.length;
  const d = M[0].length;
  const mu = new Array(d).fill(0);
  for (let j = 0; j < d; j++) {
    let s = 0;
    for (let i = 0; i < n; i++) s += M[i][j];
    mu[j] = s / n;
  }
  return mu;
}

function centerRows(M: number[][], mu: number[]): number[][] {
  return M.map((row) => row.map((v, j) => v - mu[j]));
}

/**
 * Compact SVD via one-sided Jacobi rotations.
 * Returns { U, S, Vt } where M ≈ U * diag(S) * Vt.
 */
function svd(M: number[][]): { U: number[][]; S: number[]; Vt: number[][] } {
  const m = M.length;
  const n = M[0].length;
  const tol = 1e-10;
  const maxIter = 200;

  // Work on a copy
  const A = M.map((r) => [...r]);

  // Initialize V as identity
  const V: number[][] = Array.from({ length: n }, (_, i) => {
    const row = new Array(n).fill(0);
    row[i] = 1;
    return row;
  });

  for (let iter = 0; iter < maxIter; iter++) {
    let offDiag = 0;
    for (let i = 0; i < n; i++) {
      for (let j = i + 1; j < n; j++) {
        // Compute 2x2 covariance
        let a = 0, b = 0, c = 0;
        for (let k = 0; k < m; k++) {
          a += A[k][i] * A[k][i];
          b += A[k][j] * A[k][j];
          c += A[k][i] * A[k][j];
        }
        offDiag += Math.abs(c);

        if (Math.abs(c) < tol * Math.sqrt(a * b)) continue;

        // Jacobi rotation
        const tau = (b - a) / (2 * c);
        const t = Math.sign(tau) / (Math.abs(tau) + Math.sqrt(1 + tau * tau));
        const cc = 1 / Math.sqrt(1 + t * t);
        const ss = t * cc;

        // Apply rotation to A
        for (let k = 0; k < m; k++) {
          const ai = A[k][i];
          const aj = A[k][j];
          A[k][i] = cc * ai - ss * aj;
          A[k][j] = ss * ai + cc * aj;
        }

        // Apply rotation to V
        for (let k = 0; k < n; k++) {
          const vi = V[k][i];
          const vj = V[k][j];
          V[k][i] = cc * vi - ss * vj;
          V[k][j] = ss * vi + cc * vj;
        }
      }
    }
    if (offDiag < tol) break;
  }

  // Extract singular values and form U
  const S = new Array(Math.min(m, n)).fill(0);
  const U: number[][] = Array.from({ length: m }, () =>
    new Array(Math.min(m, n)).fill(0)
  );
  for (let j = 0; j < Math.min(m, n); j++) {
    let norm = 0;
    for (let i = 0; i < m; i++) norm += A[i][j] * A[i][j];
    S[j] = Math.sqrt(norm);
    if (S[j] > tol) {
      for (let i = 0; i < m; i++) U[i][j] = A[i][j] / S[j];
    }
  }

  const Vt = transpose(V);
  return { U, S, Vt };
}

// --- Ulpia projection functions ---

export interface SvdResult {
  coords: number[][];
  residual: number[][];
}

/**
 * SVD-based PCA reduction: (n, d) → coords (n, k), residual (n, min(d-k, 3)).
 * Port of traianus.geometry.observables.svd_reduce.
 */
export function svdReduce(X: number[][], k: number = 2): SvdResult {
  const n = X.length;
  const d = X[0].length;
  if (d < k) throw new Error(`Need d >= k (${k}), got d = ${d}`);

  const mu = meanColumns(X);
  const Xc = centerRows(X, mu);
  const { U, S } = svd(Xc);

  const actualK = Math.min(k, U[0].length);
  const coords: number[][] = Array.from({ length: n }, () =>
    new Array(k).fill(0)
  );
  for (let i = 0; i < n; i++)
    for (let j = 0; j < actualK; j++) coords[i][j] = U[i][j] * S[j];

  const r = Math.min(d - k, 3);
  const residual: number[][] = Array.from({ length: n }, () =>
    new Array(r).fill(0)
  );
  for (let i = 0; i < n; i++)
    for (let j = 0; j < r; j++)
      if (k + j < U[0].length) residual[i][j] = U[i][k + j];

  return { coords, residual };
}

/**
 * Z-score + sigmoid mapping to [minVal, maxVal].
 * Port of traianus.geometry.observables.sigmoid_scale.
 */
export function sigmoidScale(
  val: number[],
  minVal: number = 0.15,
  maxVal: number = 1.0,
  eps: number = 1e-6
): number[] {
  const n = val.length;
  let sum = 0;
  for (let i = 0; i < n; i++) sum += val[i];
  const mean = sum / n;

  let sumSq = 0;
  for (let i = 0; i < n; i++) sumSq += (val[i] - mean) ** 2;
  const std = Math.sqrt(sumSq / n) + eps;

  return val.map((v) => {
    const z = (v - mean) / std;
    const sig = 1 / (1 + Math.exp(-z));
    return minVal + (maxVal - minVal) * sig;
  });
}

/**
 * Project (n, d) L2-normalized vectors to 5D effective space.
 * X, Y from top-2 SVD components (min-max to [-1,1]).
 * R, G, B from residual channels via sigmoid scaling.
 *
 * Port of traianus.geometry.observables.project_to_5d.
 */
export function projectTo5d(vectors: number[][]): number[][] {
  const n = vectors.length;
  const d = vectors[0].length;
  if (d < 5) throw new Error(`Need d >= 5, got d = ${d}`);

  const { coords, residual } = svdReduce(vectors, 2);

  // Normalize X, Y to [-1, 1]
  let maxAbs = 0;
  for (let i = 0; i < n; i++)
    for (let j = 0; j < 2; j++)
      maxAbs = Math.max(maxAbs, Math.abs(coords[i][j]));
  if (maxAbs === 0) maxAbs = 1;

  const result: number[][] = Array.from({ length: n }, () => new Array(5));
  for (let i = 0; i < n; i++) {
    result[i][0] = coords[i][0] / maxAbs;
    result[i][1] = coords[i][1] / maxAbs;
  }

  // Chromatic channels from residual
  for (let ch = 0; ch < 3; ch++) {
    const col = residual.map((r) => r[ch] ?? 0);
    const scaled = sigmoidScale(col);
    for (let i = 0; i < n; i++) result[i][2 + ch] = scaled[i];
  }

  return result;
}
