import random
import argparse
import os
import sys
import numpy as np
from deap import creator, base, tools, algorithms
from .config_loader import get_framspy_path
sys.path.append(get_framspy_path()) # FIXME: Needed so `import frams` from files in framspy are imported correctly (i.e. FramsticksLib)
from FramsticksLib import FramsticksLib
from FramsticksLibCompetition import FramsticksLibCompetition
import frams
from .other.FramsticksLibCompetitionWithHistory import FramsticksLibCompetitionWithHistory

# Note: this may be less efficient than running the evolution directly in Framsticks, so if performance is key, compare both options.


FITNESS_VALUE_INFEASIBLE_SOLUTION = -999999.0  # DEAP expects fitness to always be a real value (not None), so this special value indicates that a solution is invalid, incorrect, or infeasible. [Related: https://github.com/DEAP/deap/issues/30 ]. Using float('-inf') or -sys.float_info.max here causes DEAP to silently exit. If you are not using DEAP, set this constant to None, float('nan'), or another special/non-float value to avoid clashing with valid real fitness values, and handle such solutions appropriately as a separate case.

def genotype_within_constraint(genotype, dict_criteria_values, criterion_name, constraint_value):
	REPORT_CONSTRAINT_VIOLATIONS = False
	if constraint_value is not None:
		actual_value = dict_criteria_values[criterion_name]
		if actual_value > constraint_value:
			if REPORT_CONSTRAINT_VIOLATIONS:
				print('Genotype "%s" assigned a special ("infeasible solution") fitness because it violates constraint "%s": %s exceeds the threshold of %s' % (genotype, criterion_name, actual_value, constraint_value))
			return False
	return True


def frams_evaluate(frams_lib, individual):
	FITNESS_CRITERIA_INFEASIBLE_SOLUTION = [FITNESS_VALUE_INFEASIBLE_SOLUTION] * len(OPTIMIZATION_CRITERIA)  # this special fitness value indicates that the solution should not be propagated via selection ("that genotype is invalid"). The floating point value is only used for compatibility with DEAP. If you implement your own optimization algorithm, instead of a negative value in this constant, use a special value like None to properly distinguish between feasible and infeasible solutions.
	if not frams_lib.isValidCreature([individual[0]])[0]:
		# Short circuit if invalid genotype.
		# individual.fitness.values = (FITNESS_CRITERIA_INFEASIBLE_SOLUTION,)
		return FITNESS_CRITERIA_INFEASIBLE_SOLUTION
	genotype = individual[0]  # individual[0] because we can't (?) have a simple str as a DEAP genotype/individual, only list of str.
	data = frams_lib.evaluate([genotype])
	# print("Evaluated '%s'" % genotype, 'evaluation is:', data)
	valid = True
	try:
		first_genotype_data = data[0]
		evaluation_data = first_genotype_data["evaluations"]
		default_evaluation_data = evaluation_data[""]
		fitness = [default_evaluation_data[crit] for crit in OPTIMIZATION_CRITERIA]
	except (KeyError, TypeError) as e:  # the evaluation may have failed for an invalid genotype (such as X[@][@] with "Don't simulate genotypes with warnings" option), or because the creature failed to stabilize, or for some other reason
		valid = False
		print('Problem "%s" so could not evaluate genotype "%s", hence assigned it a special ("infeasible solution") fitness value: %s' % (str(e), genotype, FITNESS_CRITERIA_INFEASIBLE_SOLUTION))
	if valid:
		default_evaluation_data['numgenocharacters'] = len(genotype)  # add one new key to the dictionary for consistent constraint checking below
		valid &= genotype_within_constraint(genotype, default_evaluation_data, 'numparts', parsed_args.max_numparts)
		valid &= genotype_within_constraint(genotype, default_evaluation_data, 'numjoints', parsed_args.max_numjoints)
		valid &= genotype_within_constraint(genotype, default_evaluation_data, 'numneurons', parsed_args.max_numneurons)
		valid &= genotype_within_constraint(genotype, default_evaluation_data, 'numconnections', parsed_args.max_numconnections)
		valid &= genotype_within_constraint(genotype, default_evaluation_data, 'numgenocharacters', parsed_args.max_numgenochars)
	if not valid:
		fitness = FITNESS_CRITERIA_INFEASIBLE_SOLUTION
	if isinstance(frams_lib, FramsticksLibCompetitionWithHistory):
		frams_lib.updateCached(genotype, eval_fit=fitness)
		# Update CMA-ES statistics
		frams_lib.updateMutationStatistics(individual, fitness)
		# print(f'Consumed {individual.past_operations} for "{individual[0][:25].replace('\n','\\n')}"')
		individual.past_fitness = fitness
		individual.past_operations = []
	return fitness


def frams_crossover(frams_lib, individual1, individual2):
	geno1 = individual1[0]  # individual[0] because we can't (?) have a simple str as a DEAP genotype/individual, only list of str.
	geno2 = individual2[0]  # individual[0] because we can't (?) have a simple str as a DEAP genotype/individual, only list of str.
	individual1[0] = frams_lib.crossOver(geno1, geno2)
	if isinstance(frams_lib, FramsticksLibCompetitionWithHistory):
		individual1.past_operations += frams_lib.get_last_performed_operations()
	individual2[0] = frams_lib.crossOver(geno1, geno2)
	if isinstance(frams_lib, FramsticksLibCompetitionWithHistory):
		individual2.past_operations += frams_lib.get_last_performed_operations()
	return individual1, individual2


def frams_mutate(frams_lib, individual):
	individual[0] = frams_lib.mutate(individual)[0]  # individual[0] because we can't (?) have a simple str as a DEAP genotype/individual, only list of str.
	if isinstance(frams_lib, FramsticksLibCompetitionWithHistory):
		individual.past_operations += frams_lib.get_last_performed_operations()
	return individual,


def frams_getsimplest(frams_lib, genetic_format, initial_genotype):
	assert initial_genotype is None or frams.Geno.newFromString(initial_genotype).format._value() == genetic_format
	return initial_genotype if initial_genotype is not None else frams_lib.getSimplest(genetic_format)

def frams_isValid(frams_lib: FramsticksLib, individual):
	return frams_lib.isValid([individual[0]])[0]

def frams_isValidCreature(frams_lib: FramsticksLib, individual):
	return frams_lib.isValidCreature([individual[0]])[0]

def frams_getrandomindividual(frams_lib: FramsticksLib, initial_genotype):
	ind = frams_lib.getRandomGenotype(initial_genotype, 
			2,
				min(parsed_args.max_numparts if parsed_args.max_numparts is not None else 10000000000000000000, 100),
			# Movement should require at least 2 neurons: A muscle and a sensor
			min(parsed_args.max_numneurons if parsed_args.max_numneurons is not None else 10000000000000000000, 2),
				min(parsed_args.max_numneurons if parsed_args.max_numneurons is not None else 10000000000000000000, 100),
			100, True)
	return ind

def is_feasible_fitness_value(fitness_value: float) -> bool:
	assert isinstance(fitness_value, float), f"feasible_fitness({fitness_value}): argument is not of type 'float', it is of type '{type(fitness_value)}'"  # since we are using DEAP, we unfortunately must represent the fitness of an "infeasible solution" as a float...
	return fitness_value != FITNESS_VALUE_INFEASIBLE_SOLUTION  # ...so if a valid solution happens to have fitness equal to this special value, such a solution will be considered infeasible :/


def is_feasible_fitness_criteria(fitness_criteria: tuple) -> bool:
	return all(is_feasible_fitness_value(fitness_value) for fitness_value in fitness_criteria)


def select_feasible(individuals):
	"""
	Filters out only feasible individuals (i.e., with fitness different from FITNESS_VALUE_INFEASIBLE_SOLUTION).
	"""
	# for ind in individuals:
	#	print(ind.fitness.values, ind)
	feasible_individuals = [ind for ind in individuals if is_feasible_fitness_criteria(ind.fitness.values)]
	count_all = len(individuals)
	count_infeasible = count_all - len(feasible_individuals)
	if count_infeasible != 0:
		print("Selection: ignoring %d infeasible solution%s in a population of size %d" % (count_infeasible, 's' if count_infeasible > 1 else '', count_all))
	return feasible_individuals


def selTournament_only_feasible(individuals, k, tournsize):
	feasible_individuals = select_feasible(individuals)
	if len(feasible_individuals) == 0:
		print("Selection: no feasible solution in the population of size %d, so selecting from all individuals (including infeasible solutions with special fitness value %s)" % (len(individuals), FITNESS_VALUE_INFEASIBLE_SOLUTION))
		return tools.selTournament(individuals, k, tournsize=tournsize)
	return tools.selTournament(feasible_individuals, k, tournsize=tournsize)


def selNSGA2_only_feasible(individuals, k, toolboxclone):
	feasible = select_feasible(individuals)
	# tools.selNSGA2() is unfortunately unable to select more (k) from less (len(feasible)).
	# It assumes it receives at least k individuals as an argument, and only shrinks the input.
	# If it receives fewer than k individuals, the population gets permanently smaller and the k argument here decreases accordingly.
	# To prevent this, we duplicate the set of feasible individuals until it has at least k individuals:
	while len(feasible)<k:
		feasible = feasible + [toolboxclone(ind) for ind in feasible] # must copy (clone) individuals so we have independent instances in population, not multiple references to the same individuals
	return tools.selNSGA2(feasible, k)


def prepareToolbox(frams_lib, OPTIMIZATION_CRITERIA, tournament_size, genetic_format, initial_genotype):
	creator.create("FitnessMax", base.Fitness, weights=[1.0] * len(OPTIMIZATION_CRITERIA))
	creator.create("Individual", list, fitness=creator.FitnessMax, past_operations=list, past_fitness=float)  # would be nice to have "str" instead of unnecessary "list of str"

	toolbox = base.Toolbox()
	toolbox.register("attr_simplest_genotype", frams_getsimplest, frams_lib, genetic_format, initial_genotype)  # "Attribute generator"
	# (failed) struggle to have an individual which is a simple str, not a list of str
	# toolbox.register("individual", tools.initRepeat, creator.Individual, toolbox.attr_frams)
	# https://stackoverflow.com/questions/51451815/python-deap-library-using-random-words-as-individuals
	# https://github.com/DEAP/deap/issues/339
	# https://gitlab.com/santiagoandre/deap-customize-population-example/-/blob/master/AGbasic.py
	# https://groups.google.com/forum/#!topic/deap-users/22g1kyrpKy8
	toolbox.register("individual", tools.initRepeat, creator.Individual, toolbox.attr_simplest_genotype, 1)
	toolbox.register("attr_random_genotype", frams_getrandomindividual, frams_lib, toolbox.attr_simplest_genotype())  # "Attribute generator"
	def attr_random_pop_from_genotype(frams_lib, init_geno, n):
		"""
		Generate a new population by perturbing the given genotype. For use in soft_perturb_best restart method.
		"""
		pop = [tools.initRepeat(toolbox.individual_from_str, lambda: frams_lib.getRandomGenotype(init_geno,
				2,
					min(parsed_args.max_numparts if parsed_args.max_numparts is not None else 10000000000000000000, 100),
				# Movement should require at least 2 neurons: A muscle and a sensor
				min(parsed_args.max_numneurons if parsed_args.max_numneurons is not None else 10000000000000000000, 2),
					min(parsed_args.max_numneurons if parsed_args.max_numneurons is not None else 10000000000000000000, 100),
				random.randrange(0, 4), True)
			, 1) for _ in range(int(n * 0.25))]
		# Reinit with 1/4(bestratio) best ind, 3/4 randoms.
		return pop + [tools.initRepeat(toolbox.individual_from_str, toolbox.attr_random_genotype, 1) for _ in range(n - len(pop))]

	toolbox.register("attr_random_pop_from_genotype", attr_random_pop_from_genotype, frams_lib)  # "Attribute generator"
	toolbox.register("individual_from_str", creator.Individual)
	toolbox.register("random_individual", tools.initRepeat, creator.Individual, toolbox.attr_random_genotype, 1) # TODO: 
	if parsed_args.population_initialization == 'random':
		toolbox.register("population", tools.initRepeat, list, toolbox.random_individual)
	elif parsed_args.population_initialization == 'clone':
		toolbox.register("population", tools.initRepeat, list, toolbox.individual)
	toolbox.register("isValid", frams_isValidCreature, frams_lib) # frams_isValidCreature frams_isValid
	toolbox.register("evaluate", frams_evaluate, frams_lib)
	toolbox.register("mate", frams_crossover, frams_lib)
	toolbox.register("mutate", frams_mutate, frams_lib)
	if len(OPTIMIZATION_CRITERIA) <= 1:
		# toolbox.register("select", tools.selTournament, tournsize=tournament_size) # without explicitly filtering out infeasible solutions - eliminating/discriminating infeasible solutions during selection would only rely on their relatively poor fitness value
		toolbox.register("select", selTournament_only_feasible, tournsize=tournament_size)
	else:
		# toolbox.register("select", selNSGA2) # without explicitly filtering out infeasible solutions - eliminating/discriminating infeasible solutions during selection would only rely on their relatively poor fitness value
		toolbox.register("select", selNSGA2_only_feasible, toolboxclone=toolbox.clone)
	return toolbox


def parseArguments():
	parser = argparse.ArgumentParser(description='Run this program with "python -u %s" if you want to disable buffering of its output.' % sys.argv[0])
	parser.add_argument('-path', type=ensureDir, required=True, help='Path to Framsticks library without trailing slash.')
	parser.add_argument('-lib', required=False, help='Library name. If not given, "frams-objects.dll" (or .so or .dylib) is assumed depending on the platform.')
	parser.add_argument('-sim', required=False, default="eval-allcriteria.sim", help="The name of the .sim file with settings for evaluation, mutation, crossover, and similarity estimation. If not given, \"eval-allcriteria.sim\" is assumed by default. Must be compatible with the \"standard-eval\" expdef. If you want to provide more files, separate them with a semicolon ';'.")

	parser.add_argument('-genformat', required=False, help='Genetic format for the simplest initial genotype, for example 4, 9, or B. If not given, f1 is assumed.', default='1')
	parser.add_argument('-initialgenotype', required=False, help='The genotype used to seed the initial population. If given, the -genformat argument is ignored.')

	parser.add_argument('-flibclass', choices=['competition', 'wHist'], default='competition')
	parser.add_argument('-restart_patience', type=int, default=20, help=r"After how many generations of no improvement greater than 1% in the max fitness to do a restart.")
	parser.add_argument('-restart_method', choices=['hard', 'soft_perturb_best', 'soft_perturb_best_all', 'none'], default='none', help="Restart hard (so reinit pop from scratch), or soft (by applying some mutations to the best ind from the run that is ending and continuing the run)")
	parser.add_argument('-added_ind', choices=['random', 'initial'], default='initial', help="(only for AdaptMut), what genotype to add with a low probability when mutating, default: initial.")

	parser.add_argument('-opt', required=True, help='optimization criteria: vertpos, velocity, distance, vertvel, lifespan, numjoints, numparts, numneurons, numconnections (or other as long as it is provided by the .sim file and its .expdef). For multiple criteria optimization, separate the names by the comma.')
	parser.add_argument('-popsize', type=int, default=50, help="Population size, default: 50.")
	parser.add_argument('-generations', type=int, default=5, help="Number of generations, default: 5.")
	parser.add_argument('-tournament', type=int, default=5, help="Tournament size, default: 5.")
	parser.add_argument('-pmut', type=float, default=0.9, help="Probability of mutation, default: 0.9")
	parser.add_argument('-pxov', type=float, default=0.2, help="Probability of crossover, default: 0.2")
	parser.add_argument('-hof_size', type=int, default=10, help="Number of genotypes in Hall of Fame. Default: 10.")
	parser.add_argument('-hof_savefile', required=False, help='If set, Hall of Fame will be saved in the Framsticks file format (recommended extension *.gen).')

	parser.add_argument('-max_numparts', type=int, default=None, help="Maximum number of Parts. Default: no limit")
	parser.add_argument('-max_numjoints', type=int, default=None, help="Maximum number of Joints. Default: no limit")
	parser.add_argument('-max_numneurons', type=int, default=None, help="Maximum number of Neurons. Default: no limit")
	parser.add_argument('-max_numconnections', type=int, default=None, help="Maximum number of Neural connections. Default: no limit")
	parser.add_argument('-max_numgenochars', type=int, default=None, help="Maximum number of characters in genotype (including the format prefix, if any). Default: no limit")
	parsed_args = parser.parse_args()
	if parsed_args.initialgenotype == 'random':
		parsed_args.population_initialization = 'random'
		parsed_args.initialgenotype = None
	else:
		parsed_args.population_initialization = 'clone'
	return parsed_args


def ensureDir(string):
	if os.path.isdir(string):
		return string
	else:
		raise NotADirectoryError(string)


def save_genotypes(filename, OPTIMIZATION_CRITERIA, hof):
	from framsfiles import writer as framswriter
	with open(filename, "w") as outfile:
		for ind in hof:
			keyval = {}
			for i, k in enumerate(OPTIMIZATION_CRITERIA):  # construct a dictionary with criteria names and their values
				keyval[k] = ind.fitness.values[i]  # TODO it would be better to save in Individual (after evaluation) all fields returned by Framsticks, and get these fields here, not just the criteria that were actually used as fitness in evolution.
			outfile.write(framswriter.from_collection({"_classname": "org", "genotype": ind[0], **keyval}))
			outfile.write("\n")
	print("Saved '%s' (%d)" % (filename, len(hof)))


def main():
	global parsed_args, OPTIMIZATION_CRITERIA  # needed in frams_evaluate(), so made global to avoid passing as arguments

	# random.seed(123)  # see FramsticksLib.DETERMINISTIC below, set to True if you want full determinism
	FramsticksLib.DETERMINISTIC = False  # must be set before the FramsticksLib() constructor call
	parsed_args = parseArguments()
	print("Argument values:", ", ".join(['%s=%s' % (arg, getattr(parsed_args, arg)) for arg in vars(parsed_args)]))
	OPTIMIZATION_CRITERIA = parsed_args.opt.split(",")
	match parsed_args.flibclass:
		case 'competition':
			framsLib = FramsticksLibCompetition(parsed_args.path, parsed_args.lib, parsed_args.sim)
		case 'wHist':
			# Also implements Evolutionary Strategy (remembers all past mutations, and adjusts weights)
			framsLib = FramsticksLibCompetitionWithHistory(
				parsed_args.path, parsed_args.lib, parsed_args.sim, frams,
				cacheActive=False, score_fn='neg', decay=0.985,
				norm_method='mean', ESalgo='freqWindow',
			)
		case _:
			print("Unknown framslibclass", parsed_args.flibclass)
			exit(0)
	toolbox = prepareToolbox(framsLib, OPTIMIZATION_CRITERIA, parsed_args.tournament, parsed_args.genformat, parsed_args.initialgenotype)
	pop = toolbox.population(n=parsed_args.popsize)
	hof = tools.HallOfFame(parsed_args.hof_size)
	stats = tools.Statistics(lambda ind: ind.fitness.values)
	# calculate statistics excluding infeasible solutions (by filtering out those with fitness containing FITNESS_VALUE_INFEASIBLE_SOLUTION)
	def filter_feasible_for_function(function, fitness_criteria):
		filtered = list(filter(is_feasible_fitness_criteria, fitness_criteria))
		return function(filtered) if len(filtered) > 0 else float('nan')
	stats.register("avg", lambda fitness_criteria: filter_feasible_for_function(np.mean, fitness_criteria))
	stats.register("stddev", lambda fitness_criteria: filter_feasible_for_function(np.std, fitness_criteria))
	stats.register("min", lambda fitness_criteria: filter_feasible_for_function(np.min, fitness_criteria))
	stats.register("max", lambda fitness_criteria: filter_feasible_for_function(np.max, fitness_criteria))
	stats.register("totalevals", lambda _: framsLib._evaluation_count)
	stats.register("evalTime", lambda _: framsLib._evaluation_time)
	import time
	stats.register("noneval_Time", lambda _: time.perf_counter() - framsLib._time0 - framsLib._evaluation_time)
	from .dalgorithm.AdaptMut import adaptMut
	pop, log = adaptMut(
				pop, toolbox,
				cxpb=parsed_args.pxov, mutpb=parsed_args.pmut, ngen=parsed_args.generations,
				restart_method=parsed_args.restart_method, restart_patience=parsed_args.restart_patience,
				added_ind=parsed_args.added_ind,
				stats=stats, halloffame=hof, verbose=True)
	print('Best individuals:')
	for ind in hof:
		print(ind.fitness, '\t<--\t', ind[0])
	if parsed_args.hof_savefile is not None:
		save_genotypes(parsed_args.hof_savefile, OPTIMIZATION_CRITERIA, hof) # saves a *.gen file, convenient for loading into Framsticks. Otherwise, you can save the HOF in any file format you need.


if __name__ == "__main__":
	main()
