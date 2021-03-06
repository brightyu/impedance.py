from .fitting import circuit_fit, computeCircuit, calculateCircuitLength
from .plotting import plot_nyquist
import numpy as np
import os

import matplotlib as mpl
if os.environ.get('DISPLAY', '') == '':
    print('no display found. Using non-interactive Agg backend')
    mpl.use('Agg')
import matplotlib.pyplot as plt  # noqa E402


class BaseCircuit:
    """ Base class for equivalent circuit models """
    def __init__(self, initial_guess=None, name=None,
                 algorithm='leastsq', bounds=None):
        """ Base constructor for any equivalent circuit model """

        # if supplied, check that initial_guess is valid and store
        if initial_guess is not None:
            for i in initial_guess:
                assert isinstance(i, (float, int, np.int32, np.float64)),\
                    'value {} in initial_guess is not a number'.format(i)

        # initalize class attributes
        self.initial_guess = initial_guess
        self.name = name
        self.algorithm = algorithm
        self.bounds = bounds

        # initialize fit parameters and confidence intervals
        self.parameters_ = None
        self.conf_ = None

    def fit(self, frequencies, impedance):
        """ Fit the circuit model

        Parameters
        ----------
        frequencies: numpy array
            Frequencies

        impedance: numpy array of dtype 'complex128'
            Impedance values to fit

        Returns
        -------
        self: returns an instance of self

        """

        # check that inputs are valid:
        #    frequencies: array of numbers
        #    impedance: array of complex numbers
        #    impedance and frequency match in length

        assert isinstance(frequencies, np.ndarray),\
            'frequencies is not of type np.ndarray'
        assert isinstance(frequencies[0], (float, int, np.int32, np.float64)),\
            'frequencies does not contain a number'
        assert isinstance(impedance, np.ndarray),\
            'impedance is not of type np.ndarray'
        assert isinstance(impedance[0], (complex, np.complex128)),\
            'impedance does not contain complex numbers'
        assert len(frequencies) == len(impedance),\
            'mismatch in length of input frequencies and impedances'

        if self.initial_guess is not None:
            parameters, conf = circuit_fit(frequencies, impedance,
                                           self.circuit, self.initial_guess,
                                           self.algorithm,
                                           bounds=self.bounds)
            self.parameters_ = parameters
            if conf is not None:
                self.conf_ = conf
        else:
            # TODO auto calc guess
            raise ValueError('no initial guess supplied')

        return self

    def _is_fit(self):
        """ check if model has been fit (parameters_ is not None) """
        if self.parameters_ is not None:
            return True
        else:
            return False

    def predict(self, frequencies, use_initial=False):
        """ Predict impedance using a fit equivalent circuit model

        Parameters
        ----------
        frequencies: numpy array
            Frequencies

        use_initial: boolean
            If true and a fit was already completed,
            use the initial parameters instead

        Returns
        -------
        impedance: numpy array of dtype 'complex128'
            Predicted impedance

        """

        # check that inputs are valid:
        #    frequencies: array of numbers

        assert isinstance(frequencies, np.ndarray),\
            'frequencies is not of type np.ndarray'
        assert isinstance(frequencies[0], (float, int, np.int32, np.float64)),\
            'frequencies does not contain a number'

        if self._is_fit() and not use_initial:
            print("Simulating circuit based on fitted parameters")
            return computeCircuit(self.circuit, self.parameters_.tolist(),
                                  frequencies.tolist())
        else:
            print("Simulating circuit based on initial parameters")
            return computeCircuit(self.circuit, self.initial_guess,
                                  frequencies.tolist())

    def get_param_names(self):
        """Converts circuit string to names"""

        # parse the element names from the circuit string
        names = self.circuit.replace('p', '').replace('(', '').replace(')', '')
        names = names.replace(',', '-').replace('/', '-').split('-')

        return names

    def get_verbose_string(self):

        """ Defines the pretty printing of all data in the circuit"""
        names = self.get_param_names()

        to_print  = '\n-------------------------------\n'  # noqa E222
        to_print += 'Circuit: {}\n'.format(self.name)
        to_print += 'Circuit string: {}\n'.format(self.circuit)
        to_print += 'Algorithm: {}\n'.format(self.algorithm)

        if self._is_fit():
            to_print += "Fit: True\n"
        else:
            to_print += "Fit: False\n"

        to_print += '\n-------------------------------\n'
        to_print += 'Initial guesses:\n'
        for name, param in zip(names, self.initial_guess):
            to_print += '\t{} = {:.2e}\n'.format(name, param)
        if self._is_fit():
            to_print += '\n-------------------------------\n'
            to_print += 'Fit parameters:\n'
            for name, param, conf in zip(names, self.parameters_, self.conf_):
                to_print += '\t{} = {:.2e}'.format(name, param)
                to_print += '\t(+/- {:.2e})\n'.format(conf)

        return to_print

    def __str__(self):
        """ Defines the pretty printing of the circuit """

        names = self.get_param_names()

        to_print  = '\n-------------------------------\n'  # noqa E222
        to_print += 'Circuit: {}\n'.format(self.name)
        to_print += 'Circuit string: {}\n'.format(self.circuit)
        to_print += 'Algorithm: {}\n'.format(self.algorithm)

        if self._is_fit():
            to_print += "Fit: True\n"
        else:
            to_print += "Fit: False\n"

        if self._is_fit():
            to_print += '\n-------------------------------\n'
            to_print += 'Fit parameters:\n'
            for name, param, conf in zip(names, self.parameters_, self.conf_):
                to_print += '\t{} = {:.2e}\n'.format(name, param)
        else:
            to_print += '\n-------------------------------\n'
            to_print += 'Initial guesses:\n'
            for name, param in zip(names, self.initial_guess):
                to_print += '\t{} = {:.2e}\n'.format(name, param)

        return to_print

    def plot(self, f_data=None, Z_data=None, CI=True):
        """ a convenience method for plotting Nyquist plots


        Parameters
        ----------
        f_data: np.array of type float
            Frequencies of input data (for Bode plots)
        Z_data: np.array of type complex
            Impedance data to plot
        CI: boolean
            Include bootstrapped confidence intervals in plot

        Returns
        -------
        ax: matplotlib.axes
            axes of the created nyquist plot
        """

        fig, ax = plt.subplots(figsize=(5, 5))

        if Z_data is not None:
            ax = plot_nyquist(ax, f_data, Z_data)

        if self._is_fit():

            if f_data is not None:
                f_pred = f_data
            else:
                f_pred = np.logspace(5, -3)

            Z_fit = self.predict(f_pred)
            ax = plot_nyquist(ax, f_data, Z_fit, fit=True)

            if CI:
                N = 1000
                n = len(self.parameters_)
                f_pred = np.logspace(np.log10(min(f_data)),
                                     np.log10(max(f_data)),
                                     num=100)

                params = self.parameters_
                confs = self.conf_

                full_range = np.ndarray(shape=(N, len(f_pred)), dtype=complex)
                for i in range(N):
                    self.parameters_ = params + \
                                        confs*np.random.uniform(-2, 2, size=n)

                    full_range[i, :] = self.predict(f_pred)

                self.parameters_ = params

                min_Z = []
                max_Z = []
                for x in np.real(Z_fit):
                    ys = []
                    for run in full_range:
                        ind = np.argmin(np.abs(run.real - x))
                        ys.append(run[ind].imag)

                    min_Z.append(x + 1j*min(ys))
                    max_Z.append(x + 1j*max(ys))

                ax.fill_between(np.real(min_Z), -np.imag(min_Z),
                                -np.imag(max_Z), alpha='.2')

        plt.show()


class Randles(BaseCircuit):
    """ A Randles circuit model class """
    def __init__(self, CPE=False, **kwargs):
        """ Constructor for the Randles' circuit class

        Parameters
        ----------
        CPE: boolean
            Use a constant phase element instead of a capacitor
        """
        super().__init__(**kwargs)

        if CPE:
            self.name = 'Randles w/ CPE'
            self.circuit = 'R_0-p(R_1,E_1/E_2)-W_1/W_2'
            circuit_length = calculateCircuitLength(self.circuit)
            assert len(self.initial_guess) == circuit_length, \
                'Initial guess length needs to be equal to parameter length'
        else:
            self.name = 'Randles'
            self.circuit = 'R_0-p(R_1,C_1)-W_1/W_2'
            circuit_length = calculateCircuitLength(self.circuit)
            assert len(self.initial_guess) == circuit_length, \
                'Initial guess length needs to be equal to parameter length'


class CustomCircuit(BaseCircuit):
    def __init__(self, circuit=None, **kwargs):
        """ Constructor for a customizable equivalent circuit model

        Parameters
        ----------
        circuit: string
            A string that should be interpreted as an equivalent circuit


        Notes
        -----
        A custom circuit is defined as a string comprised of elements in series
        (separated by a `-`) and elements in parallel (grouped as (x,y)).
        Elements with two or more parameters are separated by a forward slash
        (`/`).

        Example:
            Randles circuit is given by 'R0-p(R1,C1)-W1/W2'



        """

        super().__init__(**kwargs)
        self.circuit = circuit

        circuit_length = calculateCircuitLength(self.circuit)
        assert len(self.initial_guess) == circuit_length, \
            'Initial guess length needs to be equal to {circuit_length}'
