"""An advanced example of iterating through the properties of an ExtValue object and printing their characteristics.
This example may be useful for some developers, but it is not needed for a regular usage of Framsticks (i.e. simulation and evolution)."""

import Disertatie.framspy.frams as frams
import sys

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

# printFramsProperties(frams.Simulator)
printFramsProperties(frams.GenMan)
# printFramsProperties(frams.World)
# printFramsProperties(frams.ExpProperties)
frams.GenMan.gen_extmutinfo = 1
print(frams.GenMan.gen_extmutinfo)
egg = frams.GenMan.crossOver(frams.Geno.newFromString('X(X,XX)XX'), frams.Geno.newFromString('XX(X,XX,X,,X)'))
printFramsProperties(egg)
print(egg.info)
exit(0)
printFramsProperties(frams.Simulator)
print(dir(frams.Simulator))

frams.Simulator.ximport("eval-allcriteria.sim", 4 + 8 + 0)
print(frams.GenMan.f0_p_swp)
frams.GenMan.f0_p_swp = 1.0
print(frams.GenMan.f0_p_swp)
# printFramsProperties(frams.World)", frams_evaluate, frams_lib

# printFramsProperties(frams.GenePools[0].add('X'))  # add('X') returns a Genotype object
from deap import creator, base, tools, algorithms

creator.create("FitnessMax", base.Fitness, weights=[1.0] * 1)
creator.create("Individual", list, fitness=creator.FitnessMax)  # would be nice to have "str" instead of unnecessary "list of str"

def frams_getsimplest(initial_genotype):
	return initial_genotype

initial_genotype = 'X'
toolbox = base.Toolbox()
toolbox.register("attr_simplest_genotype", frams_getsimplest, initial_genotype)  # "Attribute generator"

toolbox.register("individual", tools.initRepeat, creator.Individual, toolbox.attr_simplest_genotype, 1)
print(toolbox.individual())
print(type(toolbox.individual().fitness))
print(type(toolbox.individual().fitness.values))
# toolbox.individual().fitness.values = 1.0
# toolbox.register("evaluate", frams_evaluate, frams_lib)

