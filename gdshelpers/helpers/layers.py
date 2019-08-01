outlayer = 1
""" Layer for photonic devices (Waveguides, Couplers, Splitters...) """

gmarklayer = 2
""" Layer for global markers (Crosses, ...) """

lmarklayer = 3
""" Layer for local markers (Crosses, ...) """

wflayer = 4
""" Layer for write fields. (Used just for checking, not used in lithography) """

regionlayer = 5
""" Layer for region definition. (For defining working areas = multiple of writefield_size) """

framelayer = 6
""" Layer for frames. (For overall pattern and/or arrays of devices) """

patnamelayer = 7
""" Layer for pattern names. (For example NG01 CalibCoupler) """

devnamelayer = 8
""" Layer for device names. (For example A1, F0, etc..) """

parnamelayer1 = 9
""" Layer for local parameters. (Period of couplers, gaps, ...  Used for first lithography step) """

parnamelayer2 = 10
""" Layer for local parameters. (Period of couplers, gaps, ...  Used for second lithography step) """

padlayer = 11
""" Metal contact pad layer. (For probe contacts or wire bonding) """

winglayer = 12
""" Wing layer. (For connection between nanowires and pads) """

nanolayer = 13
""" Nano features layer. (SSPD wires, high resolution elements...) """

masklayer1 = 14
""" Mask window layer 1. (opening windows for subsequent etching e.g. freestanding devices) """

masklayer2 = 15
""" Mask window layer 2. (opening windows for subsequent etching e.g. freestanding devices) """

gplayers = tuple(range(16, 70))
""" List of unassigned layers for general purpose use. """
