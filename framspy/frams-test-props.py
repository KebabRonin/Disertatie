"""An advanced example of iterating through the properties of an ExtValue object and printing their characteristics.
This example may be useful for some developers, but it is not needed for a regular usage of Framsticks (i.e. simulation and evolution)."""

import framspy.frams as frams
import sys
print(sys.argv[1:])
frams.init(*(sys.argv[1:]))


def printSingleProperty(v, p):
	print(' * %s "%s" type="%s" flags=%d group=%d help="%s"' % (v._propId(p), v._propName(p), v._propType(p), v._propFlags(p), v._propGroup(p), v._propHelp(p)))


def printFramsProperties(v):
	N = v._propCount()
	G = v._groupCount()
	print("======================= '%s' has %d properties in %d group(s). =======================" % (v._class(), N, G))
	if G < 2:
		# No groups, simply iterate all properties
		for p in range(v._propCount()):
			printSingleProperty(v, p)
	else:
		# Iterate through groups and iterate all props in a group.
		# Why the distinction?
		# First, just to show there are two ways. There is always at least one
		# group so you can always get all properties by iterating the group.
		# Second, groups actually do not exist as collections. Iterating in
		# groups works by checking all properties on each iteration and
		# testing which one is the m-th property of the group!
		# So these inefficient _memberCount() and _groupMember() are provided
		# for the sake of completeness, but don't use them without a good reason ;-)
		for g in range(G):
			print('\n------------------- Group #%d: %s -------------------' % (g, v._groupName(g)))
			for m in range(v._memberCount(g)):
				p = v._groupMember(g, m)
				printSingleProperty(v, p)
	print('\n\n')

initial_genotype = """//0
p:0.6545487382828259, 0.44993558465591355, -0.11471886332450977, fr=0.105, ing=0.301
p:-0.8285715268888787, -0.32356582973110615, 0.9812965932171822, fr=0.331, ing=0.247
p:0.4820992180592969, 0.1749659053840793, -0.2822792512897073, fr=3.245, ing=0.583
p:2.214, -0.801, -0.065, fr=0.522, ing=0.492
p:2.257, -0.671, 1.044, fr=0.983, ing=0.55
p:-1.5374536615572518, 0.7129739310691106, 2.5282979875308786, fr=2.916, ing=0.509
j:3, 0, stif=0.913, rotstif=0.864
j:0, 1, stif=0.575, rotstif=0.002
j:2, 3, stif=0.227, rotstif=0.335
j:5, 1, stif=0.47, rotstif=0.635
j:4, 3, stif=0.585, rotstif=0.157
n:j=0, d="|:p=0.45, r=0.313"
n:j=1, d="|:p=0.583, r=0.641"
n:p=2, d="T:r=0.652, ry=-0.572, rz=-6.202"
n:j=2, d="|:p=0.62, r=0.905"
n:p=2, d="T:r=0.876, ry=0.014, rz=5.745"
n:j=4, d="|:p=0.121, r=0.85"
n:j=3, d="|:p=0.237, r=0.916"
n:p=1, d=S
n:j=3, d=G
n:p=0, d=S
n:p=4, d=T:ry=-2.031
n:p=5, d="T:r=0.832, ry=0.346, rz=2.758"
n:p=2, d="Gpart:ry=-2.36, rz=-1.404"
n:p=5, d=S
n:p=2, d=T:rz=0.38
n:j=4, d=G
n:p=4, d=S
n:j=1, d=G
n:p=1, d=T
n:
n:
n:d=*
c:0, 4, -1.932
c:1, 2, -1.138
c:3, 4, -11.778
c:6, 15, -0.059
c:19, 13, 2.842
c:19, 21, 1.297
c:20, 13, 3.266
c:20, 7, -0.587"""
# printFramsProperties(frams.Simulator)
# printFramsProperties(frams.GenMan)
mdl = frams.Model.newFromString(initial_genotype)
# mdl = frams.GenMan.getSimplest('4').genotype._string()
print(mdl.numparts._value())
# printFramsProperties(mdl)
# print(mdl.getJoint(0))
# printFramsProperties(mdl.getPart(0))
# print(mdl.getJoint(0).p2)
exit(0)
# printFramsProperties(frams.World)
# printFramsProperties(frams.ExpProperties)
frams.GenMan.gen_extmutinfo = 1
# print(frams.GenMan.gen_extmutinfo)
egg = frams.GenMan.crossOver(frams.Geno.newFromString('X(X,XX)XX'), frams.Geno.newFromString('XX(X,XX,X,,X)'))
# printFramsProperties(egg)
# print(egg.info)
# print(egg.format._value().__class__)
# print(frams.Geno.newFromString('X(X,XX)XX').format._value())
exit(0)
printFramsProperties(frams.Simulator)
print(dir(frams.Simulator))

frams.Simulator.ximport("eval-allcriteria.sim", 4 + 8 + 0)
# print(frams.GenMan.f0_p_swp)
frams.GenMan.f0_p_swp = 1.0
# print(frams.GenMan.f0_p_swp)
# printFramsProperties(frams.World)", frams_evaluate, frams_lib

# printFramsProperties(frams.GenePools[0].add('X'))  # add('X') returns a Genotype object
from deap import creator, base, tools, algorithms

creator.create("FitnessMax", base.Fitness, weights=[1.0] * 1)
creator.create("Individual", list, fitness=creator.FitnessMax)  # would be nice to have "str" instead of unnecessary "list of str"

def frams_getsimplest(initial_genotype):
	return initial_genotype

initial_genotype = 'X[@]X'
toolbox = base.Toolbox()
toolbox.register("attr_simplest_genotype", frams_getsimplest, initial_genotype)  # "Attribute generator"

toolbox.register("individual", tools.initRepeat, creator.Individual, toolbox.attr_simplest_genotype, 1)
# print(toolbox.individual())
# print(type(toolbox.individual().fitness))
# print(type(toolbox.individual().fitness.values))

printFramsProperties(frams.Model.newFromString(initial_genotype))
# printFramsProperties(frams.Model.newFromString(initial_genotype).getNeuroDef(0))
# toolbox.individual().fitness.values = 1.0
# toolbox.register("evaluate", frams_evaluate, frams_lib)

