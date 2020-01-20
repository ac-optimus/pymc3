#   Copyright 2020 The PyMC Developers
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
"""
Similar to disaster_model.py, but for arbitrary
deterministics which are not not working with Theano.
Note that gradient based samplers will not work.
"""


import pymc3 as pm
from theano.compile.ops import as_op
import theano.tensor as tt
from numpy import arange, array, empty

__all__ = ['disasters_data', 'switchpoint', 'early_mean', 'late_mean', 'rate',
           'disasters']

# Time series of recorded coal mining disasters in the UK from 1851 to 1962
disasters_data = array([4, 5, 4, 0, 1, 4, 3, 4, 0, 6, 3, 3, 4, 0, 2, 6,
                        3, 3, 5, 4, 5, 3, 1, 4, 4, 1, 5, 5, 3, 4, 2, 5,
                        2, 2, 3, 4, 2, 1, 3, 2, 2, 1, 1, 1, 1, 3, 0, 0,
                        1, 0, 1, 1, 0, 0, 3, 1, 0, 3, 2, 2, 0, 1, 1, 1,
                        0, 1, 0, 1, 0, 0, 0, 2, 1, 0, 0, 0, 1, 1, 0, 2,
                        3, 3, 1, 1, 2, 1, 1, 1, 1, 2, 4, 2, 0, 0, 1, 4,
                        0, 0, 0, 1, 0, 0, 0, 0, 0, 1, 0, 0, 1, 0, 1])
years = len(disasters_data)


@as_op(itypes=[tt.lscalar, tt.dscalar, tt.dscalar], otypes=[tt.dvector])
def rate_(switchpoint, early_mean, late_mean):
    out = empty(years)
    out[:switchpoint] = early_mean
    out[switchpoint:] = late_mean
    return out


with pm.Model() as model:

    # Prior for distribution of switchpoint location
    switchpoint = pm.DiscreteUniform('switchpoint', lower=0, upper=years)
    # Priors for pre- and post-switch mean number of disasters
    early_mean = pm.Exponential('early_mean', lam=1.)
    late_mean = pm.Exponential('late_mean', lam=1.)

    # Allocate appropriate Poisson rates to years before and after current
    # switchpoint location
    idx = arange(years)
    rate = rate_(switchpoint, early_mean, late_mean)

    # Data likelihood
    disasters = pm.Poisson('disasters', rate, observed=disasters_data)

    # Use slice sampler for means
    step1 = pm.Slice([early_mean, late_mean])
    # Use Metropolis for switchpoint, since it accomodates discrete variables
    step2 = pm.Metropolis([switchpoint])

    # Initial values for stochastic nodes
    start = {'early_mean': 2., 'late_mean': 3.}

    tr = pm.sample(1000, tune=500, start=start, step=[step1, step2], cores=2)
    pm.traceplot(tr)
