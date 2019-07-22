#: Layer for photonic devices (Waveguides, Couplers, Splitters...)
outlayer = 1

#: Layer for global markers (Crosses, ...)
gmarklayer = 2

#: Layer for local markers (Crosses, ...)
lmarklayer = 3

#: Layer for write fields. (Used just for checking, not used in lithography)
wflayer = 4

#: Layer for region definition. (For defining working areas = multiple of writefield_size)
regionlayer = 5

#: Layer for frames. (For overall pattern and/or arrays of devices)
framelayer = 6

#: Layer for pattern names. (For example NG01 CalibCoupler)
patnamelayer = 7

#: Layer for device names. (For example A1, F0, etc..)
devnamelayer = 8

#: Layer for local parameters. (Period of couplers, gaps, ...  Used for first lithography step)
parnamelayer1 = 9

#: Layer for local parameters. (Period of couplers, gaps, ...  Used for second lithography step)
parnamelayer2 = 10

#: Metal contact pad layer. (For probe contacts or wire bonding)
padlayer = 11

#: Wing layer. (For connection between nanowires and pads)
winglayer = 12

#: Nano features layer. (SSPD wires, high resolution elements...)
nanolayer = 13

#: Mask window layer 1. (opening windows for subsequent etching e.g. freestanding devices)
masklayer1 = 14

#: Mask window layer 2. (opening windows for subsequent etching e.g. freestanding devices)
masklayer2 = 15

#!: List of unassigned layers for general purpose use.
gplayers = tuple(range(16, 70))