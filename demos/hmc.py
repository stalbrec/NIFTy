#%%
from jax.config import config
config.update("jax_enable_x64", True)
import sys
from jax import numpy as np
from jax import random, jit, partial, lax
import jax
import matplotlib.pyplot as plt
import jifty1 as jft
from jifty1 import hmc
from functools import partial
from collections import namedtuple
from jax.tree_util import register_pytree_node
import matplotlib
matplotlib.rcParams['figure.figsize'] = (10, 7)


#%%
dims = (512,)
#datadims = (4,)
loglogslope = 2.
power_spectrum = lambda k: 1. / (k**loglogslope + 1.)
modes = np.arange((dims[0] / 2) + 1., dtype=float)
harmonic_power = power_spectrum(modes)
harmonic_power = np.concatenate((harmonic_power, harmonic_power[-2:0:-1]))


#%%
correlated_field = lambda x: jft.correlated_field.hartley(
    # x is a signal in fourier space
    # each modes amplitude gets multiplied by it's harmonic_power
    # and the whole signal is transformed back
    harmonic_power * x
)

# %% [markdown]
# signal_response = lambda x: np.exp(1. + correlated_field(x))
signal_response = lambda x: (1. + correlated_field(x))
# The signal response is $ \vec{d} = \begin{pmatrix} 1 \\ 1 \\ 1 \\ 1 \end{pmatrix} \cdot s + \vec{n} $ where $s \in \mathbb{R}$ and $\vec{n} \sim \mathcal{G}(0, N)$
# signal_response = lambda x: np.ones(shape=datadims) * x
# ???
noise_cov_inv_sqrt = lambda x: 10**-1 * x

#%%
# create synthetic data
seed = 43
key = random.PRNGKey(seed)
key, subkey = random.split(key)
# normal random fourier amplitude
pos_truth = random.normal(shape=dims, key=subkey)
signal_response_truth = signal_response(pos_truth)
key, subkey = random.split(key)
# 1. / noise_cov_inv_sqrt(np.ones(dims)) becomes the standard deviation of the noise gaussian
noise_truth = 1. / noise_cov_inv_sqrt(np.ones(dims)) * random.normal(shape=dims, key=subkey)
data = signal_response_truth + noise_truth

#%%
plt.plot(signal_response_truth, label='signal response')
#plt.plot(noise_truth, label='noise', linewidth=0.5)
plt.plot(data, label='noisy data', linewidth=1)
plt.xlabel('real space domain')
plt.ylabel('field value')
plt.legend()
plt.title("signal and data")
plt.show()

#%%
def Gaussian(data, noise_cov_inv_sqrt):
    # Simple but not very generic Gaussian energy
    # primals
    def hamiltonian(primals):
        p_res = primals - data
        # TODO: is this the weighting with noies amplitude thing again?
        l_res = noise_cov_inv_sqrt(p_res)
        return 0.5 * np.sum(l_res**2)

    return jft.Likelihood(
        hamiltonian,
    )

# negative log likelihood
nll = Gaussian(data, noise_cov_inv_sqrt) @ signal_response

#%%
ham = jft.StandardHamiltonian(likelihood=nll).jit()
ham = nll
ham_gradient = jax.grad(ham)

#%%
key, subkey = random.split(key)
initial_position = random.uniform(key=subkey, shape=pos_truth.shape)

#%%
position_samples = [initial_position]
momentum_samples = [None]
unintegrated_momenta = [None]
# this is a slight misnomer as it not only contains the rejected (i.e.
# integrated samples) but also the integration starting values (unintegrated
# samples) in the case that the proposed values were rejected.
rejected_position_samples = [None]
rejected_momentum_samples = [None]
accepted = [True]

#%% [markdown]
# # HMC with Metropolist-Hastings
key = random.PRNGKey(42)
for _ in range(100):
    key, subkey = random.split(key)
    (qp_old_and_proposed_sample, was_accepted), unintegrated_momentum = hmc.generate_hmc_sample(
        key = subkey,
        position = position_samples[-1],
        potential_energy = ham,
        potential_energy_gradient = ham_gradient,
        diagonal_momentum_covariance = np.ones(shape = initial_position.shape) * 10,
        number_of_integration_steps = 187,
        step_length = 0.0001723
    )
    position_samples.append(qp_old_and_proposed_sample[was_accepted.item()].position)
    momentum_samples.append(qp_old_and_proposed_sample[was_accepted.item()].momentum)
    rejected_position_samples.append(qp_old_and_proposed_sample[not was_accepted].position)
    rejected_momentum_samples.append(qp_old_and_proposed_sample[not was_accepted].momentum)
    unintegrated_momenta.append(unintegrated_momentum)
    accepted.append(was_accepted)
# first value is only needed during the loop
position_samples = np.array(position_samples[1:])
momentum_samples = np.array(momentum_samples[1:])
rejected_position_samples = np.array(rejected_position_samples[1:])
rejected_momentum_samples = np.array(rejected_momentum_samples[1:])
accepted = np.array(accepted[1:])
unintegrated_momenta = np.array(unintegrated_momenta[1:])

print(f"acceptance ratio: {np.sum(accepted)/len(accepted)}")

# %% [markdown]
# # HMC with Metropolist Hastings (OO wrapper)
sampler = hmc.HMCChain(
    initial_position = initial_position,
    potential_energy = ham,
    diag_mass_matrix = 1.,
    eps = 0.0001723,
    n_of_integration_steps = 187,
    rngseed = 42,
    compile = True,
    dbg_info = True
)

_last_pos, _key, position_samples, acceptance, unintegrated_momenta, momentum_samples = sampler.generate_n_samples(100)
print(f"acceptance ratio: {np.sum(acceptance)/len(acceptance)}")

# %% [markdown]
# # NUTS
sampler = hmc.NUTSChain(
    initial_position = initial_position,
    potential_energy = ham,
    diag_mass_matrix = 1.,
    eps = 1.2193,
    maxdepth = 10,
    rngseed = 42,
    compile = True,
    dbg_info = True
)

_last_pos, _key, position_samples, unintegrated_momenta, momentum_samples, depths = sampler.generate_n_samples(10000)
plt.hist(depths, bins=np.arange(sampler.maxdepth + 2))

# %% [markdown]
# # Position samples
signal_response_of_samples = lax.map(signal_response, position_samples)
mean_of_signal_response = np.mean(signal_response_of_samples, axis=0)
std_dev_of_signal_response = np.std(signal_response_of_samples, axis=0)
plt.plot(signal_response(pos_truth), label="truth")
#plt.plot(data, label="data")
#for idx, s in enumerate(position_samples[::200]):
    #plt.plot(signal_response(s), label=str(idx))
plt.plot(mean_of_signal_response, label='sample mean of signal response')
plt.fill_between(np.arange(len(mean_of_signal_response)), y1=mean_of_signal_response - std_dev_of_signal_response, y2=mean_of_signal_response + std_dev_of_signal_response, color='grey', alpha=0.5)
plt.title('position samples')
plt.xlabel('position')
plt.ylabel('signal response')
plt.legend(loc='upper right')

# %% [markdown]
# # 1D position and momentum time series
if position_samples[0].shape != (1,):
    raise ValueError("time series only availible for 1d data")
plt.plot(position_samples, label='position')
#plt.plot(momentum_samples, label='momentum', linewidth=0.2)
#plt.plot(unintegrated_momenta, label='unintegrated momentum', linewidth=0.2)
plt.title('position and momentum time series')
plt.xlabel('time')
plt.ylabel('position, momentum')
plt.legend()

# %% [markdown]
# # energy time series
potential_energies = lax.map(ham, position_samples)
kinetic_energies = np.sum(momentum_samples**2, axis=1)
#rejected_potential_energies = lax.map(ham, rejected_position_samples)
#rejected_kinetic_energies = np.sum(rejected_momentum_samples**2, axis=1)
plt.plot(potential_energies , label='pot')
plt.plot(kinetic_energies , label='kin', linewidth=1)
plt.plot(kinetic_energies + potential_energies, label='total', linewidth=1)
#plt.plot(rejected_potential_energies , label='rejected_pot')
#plt.plot(rejected_kinetic_energies , label='rejected_kin', linewidth=2)
#plt.plot(rejected_kinetic_energies + rejected_potential_energies, label='rejected_total', linewidth=0.2)
plt.xlabel('time')
plt.ylabel('energy')
plt.yscale('log')
plt.legend()

#%%
def check_leapfrog_energy_conservation():
    np.set_printoptions(precision=2)
    _dims = (2,)
    spring_constants = 100. * np.ones(shape=_dims)
    #potential_energy = lambda q: -1 / np.linalg.norm(q)
    potential_energy = lambda q: np.sum(q.T @ np.linalg.inv(np.array([[1, 0.95], [0.95, 1]])) @ q / 2.)
    potential_energy_gradient = jax.grad(potential_energy)
    mass_matrix = np.ones(shape=_dims)
    kinetic_energy = lambda p: np.sum(p**2 / mass_matrix / 2.)
    position = np.array([-1.5, -1.55])
    momentum = np.array([-1, 1]) #random.normal(key=key, shape=_dims) / mass_matrix
    positions = [position]
    momenta = [momentum]
    for _ in range(25):
        new_qp, _ = leapfrog_step(
            potential_energy_gradient=potential_energy_gradient,
            qp = QP(position=positions[-1], momentum=momenta[-1]),
            step_length=0.25
        )
        positions.append(new_qp.position)
        momenta.append(new_qp.momentum)
    positions = np.array(positions)
    momenta = np.array(momenta)
    old_pot_energy = potential_energy(position) 
    new_pot_energy = potential_energy(new_qp.position)
    g = jax.grad(potential_energy)
    print("intial gradient:", g(position))
    old_kin_energy = np.sum(momentum**2 / mass_matrix)
    new_kin_energy = np.sum(new_qp.momentum**2 / mass_matrix)
    #print("old pos:", position)
    #print("new pos:", new_qp.position)
    #print("old mom:", momentum)
    #print("new mom:", new_qp.momentum)
    print("old pot E: ", old_pot_energy)
    print("old kin E: ", old_kin_energy)
    print("old total:", old_kin_energy + old_pot_energy)
    print("new pot E: ", new_pot_energy)
    print("new kin E: ", new_kin_energy)
    print("new total:", new_kin_energy + new_pot_energy)
    print(positions)
    print(momenta)
    kinetic_energies = np.sum(momenta**2, axis=1)
    potential_energies = -1 / np.linalg.norm(positions, axis=1)
    return momenta, positions, kinetic_energies, potential_energies

momenta, positions, kinetic_energies, potential_energies = check_leapfrog_energy_conservation()


# %% [markdown]
# # Position Coordinates
plt.plot(positions[:,0], positions[:,1])
plt.xlabel("position[:,0]")
plt.ylabel("position[:,1]")


# %% [markdown]
# # Momentum coordinates
plt.plot(momenta[:,0], momenta[:,1])
plt.xlabel("momenta[:,0]")
plt.ylabel("momenta[:,1]")


# %% [markdown]
# # Value of Hamiltonian
# ## does not look exactly the same as in Neal (2011) unfortunately!
plt.plot(kinetic_energies, label='kin')
plt.plot(potential_energies, label='pot')
plt.plot(kinetic_energies + potential_energies, label='total')
plt.xlabel('time')
plt.ylabel('energy')
plt.legend()
# %%

plt.plot(data)

# %% [markdown]
# # Wiener Filter

# jax.linear_transpose for R^\dagger
# square noise_sqrt_inv ... for N^-1
# S is unit due to StandardHamiltonian
# jax.scipy.sparse.linalg.cg for D

# signal_response(s) is only needed for shape of data space
_impl_signal_response_dagger = jax.linear_transpose(signal_response, pos_truth)
signal_response_dagger = lambda d: _impl_signal_response_dagger(d)[0]
# noise_cov_inv_sqrt is diagonal
noise_cov_inv = lambda d: noise_cov_inv_sqrt(noise_cov_inv_sqrt(d))

# signal prior covariance S is assumed to be unit (see StandardHamiltonian)
# the tranposed function wierdly returns a (1,)-tuple which we unpack right here
D_inv = lambda s: s + signal_response_dagger(noise_cov_inv(signal_response(s)))

j = signal_response_dagger(noise_cov_inv(data))

m, _info = jax.scipy.sparse.linalg.cg(D_inv, j)

# %%

# TODO fix labels
plt.plot(signal_response(m), label='signal response of mean')
plt.plot(signal_response_truth, label='true signal response')
plt.legend()
plt.title('Wiener Filter')

# %%
def sample_from_d_inv(key):
    s_inv_key, rnr_key = random.split(key)
    s_inv_smpl = random.normal(s_inv_key, pos_truth.shape)
    # random.normal sample from dataspace and then R^\dagger \sqrt{N^{-1}}
    # jax.eval_shape(signal_response, pos_truth)
    rnr_smpl = signal_response_dagger(noise_cov_inv_sqrt(random.normal(rnr_key, signal_response_truth.shape)))
    return s_inv_smpl + rnr_smpl

def sample_from_d(key):
    d_inv_smpl = sample_from_d_inv(key)
    # TODO: what to do here?
    return jft.cg(D_inv, d_inv_smpl, maxiter=32)[0]

wiener_samples = np.array(list(map(
    lambda key: signal_response(sample_from_d(key) + m),
    random.split(key, 20)
)))

# %%
wiener_sample_mean = np.mean(wiener_samples, axis=0)
wiener_sample_std = np.std(wiener_samples, axis=0)

plt.plot(wiener_sample_mean)
plt.plot(signal_response(m))
for wsmpl in wiener_samples:
    pass
    plt.plot(wsmpl, color='r', linewidth=0.1)

plt.fill_between(np.arange(len(wiener_sample_mean)), y1=wiener_sample_mean - wiener_sample_std, y2=wiener_sample_mean + wiener_sample_std, color='grey', alpha=0.5)

plt.plot(np.mean(wiener_samples, axis=0), label='signal response of mean of posterior samples')
plt.legend()

# %%
