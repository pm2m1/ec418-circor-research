"""Exact NumPy port of the baseline authors' MATLAB `dwtr.m` (periodic DWT used by
Vimalajeewa et al. 2025), kept only to verify/re-create their B1 features."""
import numpy as np

SYM4_BASELINE_FILTER = np.array([-0.075765714789341, -0.029635527645954, 0.497618667632458,
                                 0.803738751805216, 0.297857795605542, -0.099219543576935,
                                 -0.012603967262261, 0.032223100604071])


def dwtr(data, L, h):
    h = np.asarray(h, float); n = len(h)
    g = h[::-1].copy(); g[0::2] = -g[0::2]
    C = np.asarray(data, float).ravel(); out = []
    for _ in range(L):
        nn = len(C)
        Cp = np.concatenate([C[np.mod(np.arange(-(n - 1), 0), nn)], C, C])
        idx = np.arange(n, n + nn - 1, 2)          # MATLAB [n:2:(n+nn-2)]+1, 1-based
        D = np.convolve(Cp, g)[idx]
        C = np.convolve(Cp, h)[idx]
        out = [D] + out
    return np.concatenate([C] + out)


def wavelet_entropy(x, h=SYM4_BASELINE_FILTER, L=1):
    J = int(np.log2(len(x)))
    wt = dwtr(x, J - L, h)
    E = np.concatenate([wt[2 ** i: 2 ** (i + 1)] ** 2 for i in range(L, J)])
    P = E / E.sum(); P = P[P != 0]
    return float(-(P * np.log2(P)).sum())


def window_entropy_cv(x_raw, win=1024):
    x = (x_raw - x_raw.mean()) / np.max(np.abs(x_raw))
    n = 2 ** int(np.floor(np.log2(len(x))))
    y = x[:n]
    hs = np.array([wavelet_entropy(y[k:k + win]) for k in range(0, n, win)])
    a = hs[hs != 0]
    return float(a.std(ddof=1) / a.mean())
