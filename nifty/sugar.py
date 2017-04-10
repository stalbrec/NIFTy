# -*- coding: utf-8 -*-

from nifty import PowerSpace,\
                  Field,\
                  DiagonalOperator,\
                  FFTOperator

__all__ = ['create_power_operator']


def create_power_operator(domain, power_spectrum, dtype=None,
                          distribution_strategy='not'):
    if not domain.harmonic:
        fft = FFTOperator(domain)
        domain = fft.target[0]

    power_domain = PowerSpace(domain,
                              dtype=dtype,
                              distribution_strategy=distribution_strategy)

    fp = Field(power_domain,
               val=power_spectrum,
               distribution_strategy=distribution_strategy)

    f = fp.power_synthesize(mean=1, std=0, real_signal=False)

    power_operator = DiagonalOperator(domain, diagonal=f, bare=True)

    return power_operator
