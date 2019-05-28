from time import time

import matplotlib.pyplot as plt
import numpy as np

import nifty5 as ift

np.random.seed(40)

N0s, a0s, b0s, c0s = [], [], [], []

for ii in range(10, 26):
    nu = 2048
    nv = 2048
    N = int(2**ii)
    print('N = {}'.format(N))

    uvw = np.random.rand(N, 3) - 0.5
    vis = np.random.randn(N) + 1j*np.random.randn(N)

    uvspace = ift.RGSpace((nu, nv))

    visspace = ift.UnstructuredDomain(N)

    img = np.random.randn(nu*nv)
    img = img.reshape((nu, nv))
    img = ift.from_global_data(uvspace, img)

    t0 = time()
    GM = ift.GridderMaker(uvspace, eps=1e-7, uvw=uvw,
                          channel_fact=np.array([1.]),
                          flags=np.zeros((N, 1), dtype=np.bool))
    vis = ift.from_global_data(visspace, vis)
    op = GM.getFull().adjoint
    t1 = time()
    op(img).to_global_data()
    t2 = time()
    op.adjoint(vis).to_global_data()
    t3 = time()
    print(t2-t1, t3-t2)
    N0s.append(N)
    a0s.append(t1 - t0)
    b0s.append(t2 - t1)
    c0s.append(t3 - t2)

print('Measure rest operator')
sc = ift.StatCalculator()
op = GM.getRest().adjoint
for _ in range(10):
    t0 = time()
    res = op(img)
    sc.add(time() - t0)
t_fft = sc.mean
print('FFT shape', res.shape)

plt.scatter(N0s, a0s, label='Gridder mr')
plt.legend()
# no idea why this is necessary, but if it is omitted, the range is wrong
plt.ylim(min(a0s), max(a0s))
plt.ylabel('time [s]')
plt.title('Initialization')
plt.loglog()
plt.savefig('bench0.png')
plt.close()

plt.scatter(N0s, b0s, color='k', marker='^', label='Gridder mr times')
plt.scatter(N0s, c0s, color='k', label='Gridder mr adjoint times')
plt.axhline(sc.mean, label='FFT')
plt.axhline(sc.mean + np.sqrt(sc.var))
plt.axhline(sc.mean - np.sqrt(sc.var))
plt.legend()
plt.ylabel('time [s]')
plt.title('Apply')
plt.loglog()
plt.savefig('bench1.png')
plt.close()
