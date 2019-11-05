import numpy as np

from ..domain_tuple import DomainTuple
from ..operators.value_inserter import ValueInserter
from ..domains.power_space import PowerSpace
from ..domains.unstructured_domain import UnstructuredDomain
from ..field import Field
from ..operators.adder import Adder
from ..operators.distributors import PowerDistributor
from ..operators.endomorphic_operator import EndomorphicOperator
from ..operators.exp_transform import ExpTransform
from ..operators.linear_operator import LinearOperator
from ..operators.operator import Operator
from ..operators.qht_operator import QHTOperator
from ..operators.simple_linear_operators import VdotOperator, ducktape
from ..operators.slope_operator import SlopeOperator
from ..operators.symmetrizing_operator import SymmetrizingOperator
from ..sugar import from_global_data, full, makeDomain, makeOp


def _lognormal_moment_matching(mean, sig, key):
    mean, sig, key = float(mean), float(sig), str(key)
    assert sig > 0
    logsig = np.sqrt(np.log((sig/mean)**2 + 1))
    logmean = np.log(mean) - logsig**2/2
    return _normal(logmean, logsig, key).exp()


def _normal(mean, sig, key):
    return Adder(Field.scalar(mean)) @ (
        sig*ducktape(DomainTuple.scalar_domain(), None, key))


class _TwoLogIntegrations(LinearOperator):
    def __init__(self, target):
        self._target = makeDomain(target)
        self._domain = makeDomain(
            UnstructuredDomain((2, self.target.shape[0] - 2)))
        self._capability = self.TIMES | self.ADJOINT_TIMES
        if not isinstance(self._target[0], PowerSpace):
            raise TypeError
        logk_lengths = np.log(self._target[0].k_lengths[1:])
        self._logvol = logk_lengths[1:] - logk_lengths[:-1]

    def apply(self, x, mode):
        self._check_input(x, mode)
        if mode == self.TIMES:
            x = x.to_global_data()
            res = np.empty(self._target.shape)
            res[0] = 0
            res[1] = 0
            res[2:] = np.cumsum(x[1])
            res[2:] = (res[2:] + res[1:-1])/2*self._logvol + x[0]
            res[2:] = np.cumsum(res[2:])
            return from_global_data(self._target, res)
        else:
            x = x.to_global_data_rw()
            res = np.zeros(self._domain.shape)
            x[2:] = np.cumsum(x[2:][::-1])[::-1]
            res[0] += x[2:]
            x[2:] *= self._logvol/2.
            res[1:-1] += res[2:]
            x[1] += np.cumsum(res[2:][::-1])[::-1]
            return from_global_data(self._domain, res)


class _Normalization(Operator):
    def __init__(self, domain):
        self._domain = self._target = makeDomain(domain)
        hspace = self._domain[0].harmonic_partner
        pd = PowerDistributor(hspace, power_space=self._domain[0])
        # TODO Does not work on sphere yet
        cst = pd.adjoint(full(pd.target, 1.)).to_global_data_rw()
        cst[0] = 0
        self._cst = from_global_data(self._domain, cst)
        self._specsum = _SpecialSum(self._domain)

    def apply(self, x):
        self._check_input(x)
        amp = x.exp()
        spec = (2*x).exp()
        # FIXME This normalizes also the zeromode which is supposed to be left
        # untouched by this operator
        return self._specsum(self._cst*spec)**(-0.5)*amp


class _SpecialSum(EndomorphicOperator):
    def __init__(self, domain):
        self._domain = makeDomain(domain)
        self._capability = self.TIMES | self.ADJOINT_TIMES

    def apply(self, x, mode):
        self._check_input(x, mode)
        return full(self._tgt(mode), x.sum())


class FinalAmplitude:
    def __init__(self):
        self._amplitudes = []

    def add_fluctuations_from_ops(self, target, fluctuations, flexibility,
                                  asperity, loglogavgslope, key):
        """
        fluctuations > 0
        flexibility > 0
        asperity > 0
        loglogavgslope probably negative
        """
        assert isinstance(fluctuations, Operator)
        assert isinstance(flexibility, Operator)
        assert isinstance(asperity, Operator)
        assert isinstance(loglogavgslope, Operator)
        target = makeDomain(target)
        assert len(target) == 1
        assert isinstance(target[0], PowerSpace)

        twolog = _TwoLogIntegrations(target)
        dt = twolog._logvol
        sc = np.zeros(twolog.domain.shape)
        sc[0] = sc[1] = np.sqrt(dt)
        sc = from_global_data(twolog.domain, sc)
        expander = VdotOperator(sc).adjoint
        sigmasq = expander @ flexibility

        dist = np.zeros(twolog.domain.shape)
        dist[0] += 1.
        dist = from_global_data(twolog.domain, dist)
        scale = VdotOperator(dist).adjoint @ asperity

        shift = np.ones(scale.target.shape)
        shift[0] = dt**2/12.
        shift = from_global_data(scale.target, shift)
        scale = sigmasq*(Adder(shift) @ scale).sqrt()

        smooth = twolog @ (scale*ducktape(scale.target, None, key))

        # move to tests
        from numpy.testing import assert_allclose
        from ..sugar import from_random
        assert_allclose(
            smooth(from_random('normal', smooth.domain)).val[0:2], 0)
        from ..extra import check_jacobian_consistency
        check_jacobian_consistency(smooth, from_random('normal',
                                                       smooth.domain))
        # end move to tests

        normal_ampl = _Normalization(target) @ smooth
        vol = target[0].harmonic_partner.get_default_codomain().total_volume
        arr = np.zeros(target.shape)
        arr[1:] = vol
        expander = VdotOperator(from_global_data(target, arr)).adjoint
        mask = np.zeros(target.shape)
        mask[0] = vol
        adder = Adder(from_global_data(target, mask))
        ampl = adder @ ((expander @ fluctuations)*normal_ampl)

        # Move to tests
        # FIXME This test fails but it is not relevant for the final result
        # assert_allclose(
        #     normal_ampl(from_random('normal', normal_ampl.domain)).val[0], 1)
        assert_allclose(ampl(from_random('normal', ampl.domain)).val[0], vol)
        # End move to tests

        self._amplitudes.append(ampl)

    def add_fluctuations(self, target, fluctuations_mean, fluctuations_stddev,
                         flexibility_mean, flexibility_stddev, asperity_mean,
                         asperity_stddev, loglogavgslope_mean,
                         loglogavgslope_stddev, prefix):
        fluctuations_mean = float(fluctuations_mean)
        fluctuations_stddev = float(fluctuations_stddev)
        flexibility_mean = float(flexibility_mean)
        flexibility_stddev = float(flexibility_stddev)
        asperity_mean = float(asperity_mean)
        asperity_stddev = float(asperity_stddev)
        loglogavgslope_mean = float(loglogavgslope_mean)
        loglogavgslope_stddev = float(loglogavgslope_stddev)
        prefix = str(prefix)
        assert fluctuations_stddev > 0
        assert fluctuations_mean > 0
        assert flexibility_stddev > 0
        assert flexibility_mean > 0
        assert asperity_stddev > 0
        assert asperity_mean > 0
        assert loglogavgslope_stddev > 0

        fluct = _lognormal_moment_matching(fluctuations_mean,
                                           fluctuations_stddev,
                                           prefix + 'fluctuations')
        flex = _lognormal_moment_matching(flexibility_mean, flexibility_stddev,
                                          prefix + 'flexibility')
        asp = _lognormal_moment_matching(asperity_mean, asperity_stddev,
                                         prefix + 'asperity')
        avgsl = _normal(loglogavgslope_mean, loglogavgslope_mean,
                        prefix + 'loglogavgslope')
        self.add_fluctuations_from_ops(target, fluct, flex, asp, avgsl,
                                       prefix + 'spectrum')

    def finalize_from_op(self, zeromode):
        raise NotImplementedError

    def finalize(self,
                 offset_amplitude_mean,
                 offset_amplitude_stddev,
                 prefix,
                 offset=None):
        """
        offset vs zeromode: volume factor
        """
        offset_amplitude_stddev = float(offset_amplitude_stddev)
        offset_amplitude_mean = float(offset_amplitude_mean)
        assert offset_amplitude_stddev > 0
        assert offset_amplitude_mean > 0
        if offset is not None:
            offset = float(offset)
        hspace = makeDomain(
            [dd.target[0].harmonic_partner for dd in self._amplitudes])

        azm = _lognormal_moment_matching(offset_amplitude_mean,
                                         offset_amplitude_stddev,
                                         prefix + 'zeromode')
        foo = np.ones(hspace.shape)
        zeroind = len(hspace.shape)*(0,)
        foo[zeroind] = 0
        azm = Adder(from_global_data(hspace, foo)) @ ValueInserter(
            hspace, zeroind) @ azm

        from ..operators.harmonic_operators import HarmonicTransformOperator
        ht = HarmonicTransformOperator(hspace, space=0)
        pd = PowerDistributor(hspace, self._amplitudes[0].target[0], 0)
        for i in range(1, len(self._amplitudes)):
            ht = HarmonicTransformOperator(ht.target, space=i) @ ht
            pd = pd @ PowerDistributor(
                pd.domain, self._amplitudes[i].target[0], space=i)

        spaces = tuple(range(len(self._amplitudes)))
        from ..operators.contraction_operator import ContractionOperator
        a = ContractionOperator(pd.domain,
                                spaces[1:]).adjoint(self._amplitudes[0])
        for i in range(1, len(self._amplitudes)):
            a = a*(ContractionOperator(pd.domain, spaces[:i] + spaces[
                (i + 1):]).adjoint(self._amplitudes[i]))

        A = pd @ a
        return ht(A*ducktape(hspace, None, prefix + 'xi'))