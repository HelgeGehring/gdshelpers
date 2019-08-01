from enum import Enum


class _Configuration(object):
    DefaultDatatype = Enum('DefaultDatatype', 'zero aslayer dose_factor')

    _datatype = DefaultDatatype.aslayer
    _dose_factor = 1.0
    _point_limit = 4000
    _point_limit_line = 4000

    MACHINE_DEFAULTS = {
        'unlimited': {
            'datatype_policy': DefaultDatatype.zero,
            'dose_factor': 1.,
            'point_limit': None,
            'point_limit_line': None
        },
        'JEOL': {
            'datatype_policy': DefaultDatatype.aslayer,
            'dose_factor': 1.,
            'point_limit': 4000,
            'point_limit_line': 4000
        },
        'E-Line': {
            'datatype_policy': DefaultDatatype.dose_factor,
            'dose_factor': 1.,
            'point_limit': 4000,
            'point_limit_line': 4000
        },
        'conservative': {
            'datatype_policy': DefaultDatatype.zero,
            'dose_factor': 1.,
            'point_limit': 200,
            'point_limit_line': 200
        }
    }

    @property
    def datatype_policy(self):
        return self._datatype

    @datatype_policy.setter
    def datatype_policy(self, policy):
        assert policy in self.DefaultDatatype
        self._datatype = policy

    @property
    def dose_factor(self):
        return self._dose_factor

    @dose_factor.setter
    def dose_factor(self, dose_factor):
        self._dose_factor = float(dose_factor)

    @property
    def point_limit(self):
        return self._point_limit

    @point_limit.setter
    def point_limit(self, max_points):
        assert type(max_points) == int and max_points > 5
        self._point_limit = max_points

    @property
    def point_limit_line(self):
        return self._point_limit

    @point_limit_line.setter
    def point_limit_line(self, max_points_line):
        assert type(max_points_line) == int and max_points_line > 5
        self._point_limit_line = max_points_line

    def set_target_profile(self, profile_name):
        assert profile_name in self.MACHINE_DEFAULTS, 'Profile name must be one of %s' % self.MACHINE_DEFAULTS.keys()

        for key, value in self.MACHINE_DEFAULTS[profile_name].items():
            self.__setattr__(key, value)
