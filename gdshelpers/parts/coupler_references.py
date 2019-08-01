"""
This module includes a collection of coupler parameters. It is not meant to be used directly but
rather via the :func:`GratingCoupler.make_traditional_coupler_from_database` functions.

Feel free to report your coupler findings for inclusion in this database.
"""

import numpy as np

REFERENCES = {
    ##########
    # The definitions following below were extracted from the lib/coupler
    # directory. I don't know how trustworthy they are. If you have corrections
    # or recommendations just let me know.

    'aln660': {
        'parameters': {
            'full_opening_angle': np.deg2rad(40.0),
            'grating_period': lambda wavelength: (wavelength + 575.9965) / 2772.187,
            'grating_ff': 0.72,
            'n_gratings': 20,
        },
        'meta': {
            'origin': 'lib/coupler/coupler_aln660.il',
            'comment': 'Wavelength corrected Dec-20-2010 by Wolfram Pernice, chip R10-6'
        }
    },

    'aln780': {
        'parameters': {
            'full_opening_angle': np.deg2rad(40.0),
            'grating_period': lambda wavelength: (wavelength - 363.214) / 826.55,
            'grating_ff': 0.8,
            'n_gratings': 30,
        },
        'meta': {
            'origin': 'lib/coupler/coupler_aln780.il',
            'comment': 'Wavelength corrected 03-03-2011, WP from chip R32'
        }
    },

    'aln780_ox': {
        'parameters': {
            'full_opening_angle': np.deg2rad(40.0),
            'grating_period': lambda wavelength: (wavelength - 450.02925) / 662.87,
            'grating_ff': 0.76,
            'n_gratings': 30,
        },
        'meta': {
            'origin': 'lib/coupler/coupler_aln780.il',
            'comment': 'Wavelength corrected 03-09-2011, WP from chip R30 + oxide'
        }
    },

    'aln1230': {
        'parameters': {
            'full_opening_angle': np.deg2rad(40.0),
            'grating_period': lambda wavelength: (wavelength - 280.060566) / 1223.47208,
            'grating_ff': 0.8,
            'n_gratings': 20,
        },
        'meta': {
            'origin': 'lib/coupler/coupler_aln1230.il',
            'comment': ''
        }
    },

    'aln1550': {
        'parameters': {
            'full_opening_angle': np.deg2rad(40.0),
            'grating_period': lambda wavelength: (wavelength - 112.258) / 1220.68,
            # NOTE: Before changed by Matthias Stegmaier, this was (wavelength - 796.566)/690.4757
            #      As corrected Mar-03-2011 by Wolfram Pernice, chip R29.
            'grating_ff': 0.85,
            'n_gratings': 20,
        },
        'meta': {
            'origin': 'lib/coupler/coupler_aln1550.il',
            'comment': 'Wavelength corrected 2012-08-06 by Matthias Stegmaier, MS003'
        }
    },

    # It is not clear what thick means in this context but this definition also
    # includes the taper length.
    'aln1550_thick': {
        'parameters': {
            'full_opening_angle': np.deg2rad(40.0),
            'grating_period': lambda wavelength: (wavelength - 1045.0715) / 454.29771,
            'grating_ff': 0.65,
            'n_gratings': 20,
            'taper_length': 30,
        },
        'meta': {
            'origin': 'lib/coupler/coupler_aln1550.il',
            'comment': 'Wavelength corrected Sep-12-2011 by Wolfram Pernice, chip CP4'
        }
    },

    # NOTE: coupler_bto* was not included, as I don't know what to make of them
    # NOTE: coupler_diamond* was not included, as I don't know what to make of them

    'gan780': {
        'parameters': {
            'full_opening_angle': np.deg2rad(40.0),
            'grating_period': lambda wavelength: (wavelength - 438.75) / 750,
            'grating_ff': 0.72,
            'n_gratings': 20,
        },
        'meta': {
            'origin': 'lib/coupler/coupler_gan780.il',
            'comment': 'Wavelength measured results: 11-01-2010'
        }
    },

    'gan1550': {
        'parameters': {
            'full_opening_angle': np.deg2rad(40.0),
            'grating_period': lambda wavelength: (wavelength - 1197.31738) / 343.49,
            'grating_ff': 0.8,
            'n_gratings': 20,
        },
        'meta': {
            'origin': 'lib/coupler/coupler_gan780.il',
            'comment': 'Wavelength based on Oct2010 GNC1 device results measured 11-01-2010'
        }
    },

    # NOTE: coupler_gan_shg not included, as I don't know what to make of them

    'hs110': {
        'parameters': {
            'full_opening_angle': np.deg2rad(40.0),
            'grating_period': lambda wavelength: (wavelength - 336.4172) / 1710.5,
            'grating_ff': 0.525,
            'n_gratings': 20,
        },
        'meta': {
            'origin': 'lib/coupler/coupler_gan780.il',
            'comment': ''
        }
    },

    'hs110_ox': {
        'parameters': {
            'full_opening_angle': np.deg2rad(40.0),
            'grating_period': lambda wavelength: (wavelength - 317.1553) / 1760.4,
            'grating_ff': 0.5,
            'n_gratings': 20,
        },
        'meta': {
            'origin': 'lib/coupler/coupler_gan780.il',
            'comment': ''
        }
    },

    # NOTE: coupler_opt not included, as I don't know what to make of them
    # NOTE: coupler_shg not included, as I don't know what to make of them

    'si110': {
        'parameters': {
            'full_opening_angle': np.deg2rad(40.0),
            'grating_period': lambda wavelength: (wavelength - 728.6) / 917.0,
            'grating_ff': 0.8,
            'n_gratings': 20,
        },
        'meta': {
            'origin': 'lib/coupler/coupler_si110.il',
            'comment': 'Wavelength newly corrected formula base on Jun2008 device results'
        }
    },

    'si110_ox': {
        'parameters': {
            'full_opening_angle': np.deg2rad(40.0),
            'grating_period': lambda wavelength: (wavelength - 898.22) / 784.3,
            'grating_ff': 0.8,
            'n_gratings': 20,
        },
        'meta': {
            'origin': 'lib/coupler/coupler_si110.il',
            'comment': 'Wavelength newly corrected formula base on Jun2010 device results (C3) with 1200nm PECVD oxide'
        }
    },

    'si110_nb': {
        'parameters': {
            'full_opening_angle': np.deg2rad(40.0),
            'grating_period': lambda wavelength: (wavelength - 942.8254) / 663.2421,
            'grating_ff': 0.8,
            'n_gratings': 20,
        },
        'meta': {
            'origin': 'lib/coupler/coupler_si110.il',
            'comment': 'Wavelength newly corrected formula base on Jun2010 device results (C3) with 1200nm PECVD oxide'
        }
    },

    'si110_ap': {
        'parameters': {
            'full_opening_angle': np.deg2rad(40.0),
            'grating_period': lambda wavelength: (wavelength - 728.6) / 917.0,
            'grating_ff': 0.8,
            'n_gratings': 20,
            'n_ap_gratings': 10,
        },
        'meta': {
            'origin': 'lib/coupler/coupler_si110.il',
            'comment': 'Wavelength newly corrected formula base on Jun2008 device results'
        }
    },

    'si110_nb_ap': {
        'parameters': {
            'full_opening_angle': np.deg2rad(40.0),
            'grating_period': lambda wavelength: (wavelength - 942.8254) / 663.2421,
            'grating_ff': 0.8,
            'n_gratings': 20,
            'n_ap_gratings': 10,
        },
        'meta': {
            'origin': 'lib/coupler/coupler_si110.il',
            'comment': 'Wavelength newly corrected formula 06-24-2011 from device J16'
        }
    },

    'si220': {
        'parameters': {
            'full_opening_angle': np.deg2rad(40.0),
            'grating_period': lambda wavelength: (wavelength * 0.715 - 389.74) / 1000.0,
            'grating_ff': 0.8,
            'n_gratings': 20,
        },
        'meta': {
            'origin': 'lib/coupler/coupler_si220.il',
            'comment': 'Wavelength corrected 05/04/2010'
        }
    },

    'sin500': {
        'parameters': {
            'full_opening_angle': np.deg2rad(40.0),
            'grating_period': lambda wavelength: (wavelength - 198.4740) / 1353.5,
            'grating_ff': 0.4,
            'n_gratings': 20,
        },
        'meta': {
            'origin': 'lib/coupler/coupler_sin500.il',
            'comment': ''
        }
    },

    'sn200_va': {
        'parameters': {
            'full_opening_angle': np.deg2rad(40.0),
            'grating_period': lambda wavelength: (wavelength - 201.34) / 955.1,
            'grating_ff': 0.8,
            'n_gratings': 30,
        },
        'meta': {
            'origin': 'lib/coupler/coupler_sn200_va.il',
            'comment': 'Wavelength formula base on Comsol simulation'
        }
    },

    'sn200_vw': {
        'parameters': {
            'full_opening_angle': np.deg2rad(40.0),
            'grating_period': lambda wavelength: (wavelength - 235.6) / 879.1,
            'grating_ff': 0.65,
            'n_gratings': 30,
        },
        'meta': {
            'origin': 'lib/coupler/coupler_sn200_vw.il',
            'comment': 'Wavelength formula base on Comsol simulation'
        }
    },

    'sn330': {
        'parameters': {
            'full_opening_angle': np.deg2rad(40.0),
            'grating_period': lambda wavelength: (wavelength - 620.012) / 816.57,
            'grating_ff': 0.85,
            'n_gratings': 20,
        },
        'meta': {
            'origin': 'lib/coupler/coupler_sn330',
            'comment': 'Wavelength changed 06/03/2010 by WP'
        }
    },

}
