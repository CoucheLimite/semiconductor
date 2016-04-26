import numpy as np
import ConfigParser
import os
import sys
from semiconductor.helper.helper import HelperFunctions

# the idea is to have one class (opticalProperties)
# which is connectd to many other smaller class that provide
# n, absorption/k,


class TabulatedOpticalProperties():
    temp = 300
    ext_cof = False

    def __init__(self, material='Si', abs_author=None, ref_author=None, temp=None):
        self.temp = temp or self.temp
        self.tac = TabulatedAbsorptionCoefficient(material, abs_author, temp)
        self.tri = TabulatedRefractiveIndex(material, ref_author, temp)
        self.load()

    def load(self, abs_author=None, ref_author=None, temp=None, common_range=True):
        self.tac.load(abs_author, temp)
        self.tri.load(ref_author, temp)

        self.abs_cof_bb = self.tac.abs_cof_bb
        self.ref_ind = self.tri.ref_ind

        if self.ext_cof:
            self.ext_cof_bb = self.tac.caculate_ext_coef()

        if common_range:
            # set the values
            self.wavelength = self.tac.wavelength
            self.energy = self.tac.energy

            # update the refractive index
            self.ref_ind = self.tri.ref_ind_at_wls(self.wavelength)

            # remove unused variables
            self.wl_abs_cof_bb = None
            self.wl_ref_ind = None
        else:
            # just use as is
            self.wl_abs_cof_bb = self.tac.wl
            self.wl_ref_ind = self.tri.wl

            # remove unused variables
            self.wavelength = None

        pass


class TabulatedAbsorptionCoefficient(HelperFunctions):

    """
    A class containg the optical constants of silicon
    These are temperature dependence.
    """
    temp = 300.
    file_for_models = r'tabulated_absorption_coefficient.const'

    def __init__(self, material='Si', author=None, temp=None):
        self.temp = temp or self.temp

        self.author = author
        self.material = material

        self.Models = ConfigParser.ConfigParser()

        constants_file = os.path.join(
            os.path.dirname(__file__),
            material,
            self.file_for_models)

        self.Models.read(constants_file)

        self.load()

    def load(self, author=None, temp=None):
        """
        Loads alpha and n
        from the provided or from self. the name
        """
        # check to see if its set here out outside of this function
        author = author or self.author
        temp = temp or self.temp

        self.change_model(author)

        # Getting the absorption coefficient from a file
        data = np.genfromtxt(os.path.join(os.path.dirname(__file__),
                                          self.material,
                                          self.model),
                             names=True, delimiter=',')

        # need something here to get temp dependence
        self.wavelength, self.energy = data[
            'wavelength'], data['energy']

        if type(self.vals['temp']) is float:
            self.abs_cof_bb = data['alpha']
            if temp != self.vals['temp']:
                try:
                    self.abs_cof_bb = _temp_power_law(
                        self.abs_cof_bb, data['C_ka'], temp, self.vals['temp'])
                except:
                    print 'Temp Warning:'
                    print '\tNo tabulated data, or temp cofs for {0:.0f} K'.format(temp)
                    print '\tfor the author {0}'.format(author)
                    print '\tusing data for temperature {0:.0f} K.'.format(self.vals['temp'])

        else:
            # this happens when there are several alpha values, so lets try a
            # specif temp
            name = 'alpha_{0:.0f}K'.format(temp)
            if name in data.dtype.names:
                self.abs_cof_bb = data[name]
            else:
                # if doesn't work just use the stipulated default
                print 'Temp Warning:'
                print '\tTabulated data at', temp, 'K does not exist.'
                print '\tfor the author {0}'.format(author)
                print '\tThe value for', self.vals['default_temp'],
                print 'K is used'
                name = 'alpha_{0:.0f}K'.format(self.vals['default_temp'])
                self.abs_cof_bb = data[name]

        try:
            # get the uncertainty
            self.U = data['U']

        except:
            pass

    def alphaBB_at_wls(self, wavelength):
        return np.interp(wavelength,
                         self.wavelength,
                         self.abs_cof_bb)

    def caculate_ext_coef(self):
        self.ext_cof_bb = self.abs_cof_bb * self.wavelength / 4 / np.pi
        return self.ext_cof_bb


class TabulatedRefractiveIndex(HelperFunctions):

    temp = 300.
    file_for_models = r'tabulated_refractive_index.const'

    def __init__(self, material='Si', author=None, temp=None):

        # set values
        self.author = author
        self.material = material
        self.temp = temp or self.temp

        self.Models = ConfigParser.ConfigParser()

        constants_file = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            material,
            self.file_for_models)

        self.Models.read(constants_file)

        self.load()

    def load(self, author=None, temp=None):
        """
        Loads n
        from the provided or from self. the name
        """

        # check to see if its set here out outside of this function
        author = author or self.author
        temp = temp or self.temp

        # Get the dets
        self.change_model(author)

        # To do
        # need to make a check if there is a temp value
        # if there is use it, if not check if there are temp coefficients
        # there there are use them
        # if nothing return the default temp value.

        # Get n
        data = np.genfromtxt(os.path.join(os.path.dirname(__file__),
                                          self.material,
                                          self.model),
                             names=True, delimiter=',')

        self.wavelength, self.ref_ind, self.energy = data[
            'wavelength'], data['n'], data['energy']

        if temp != self.vals['temp']:
            try:
                self.ref_ind = _temp_power_law(
                    self.ref_ind, data['C_n'], temp, self.vals['temp'])
            except:
                print 'Temp Warning:'
                print '\tNo tabulated data, or temp cofs for {0:.0f} K'.format(temp)
                print '\tfor the author {0}'.format(author)
                print '\tusing data for temperature {0:.0f} K.'.format(self.vals['temp'])

    def ref_ind_at_wls(self, wavelength):
        '''
        returns the refrative index n's
        and the supplied wavelengths

        inputs:
            wavelength (array)
        output:
            n (array)
        '''
        return np.interp(wavelength,
                         self.wavelength,
                         self.ref_ind)


def _temp_power_law(ref_vairable, coef, temp, ref_temp):
    return ref_vairable * np.power(temp / ref_temp, coef)
