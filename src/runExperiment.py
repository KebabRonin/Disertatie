import argparse
import os
import sys
import numpy as np
from deap import creator, base, tools, algorithms
from framspy.FramsticksLib import FramsticksLib, DissimMethod
from framspy.FramsticksLibCompetition import FramsticksLibCompetition

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
	genotype = individual[0]  # individual[0] because we can't (?) have a simple str as a DEAP genotype/individual, only list of str.
	data = frams_lib.evaluate([genotype])
	# print("{'genotype': \"" + genotype.replace('\n', '\\n') + "\", 'data': " + str(data) + "}", file=sys.stderr)
	valid = True
	try:
		first_genotype_data = data[0]
		evaluation_data = first_genotype_data["evaluations"]
		default_evaluation_data = evaluation_data[""]
		fitness = [default_evaluation_data[crit] for crit in OPTIMIZATION_CRITERIA]
	except (KeyError, TypeError) as e:  # the evaluation may have failed for an invalid genotype (such as X[@][@] with "Don't simulate genotypes with warnings" option), or because the creature failed to stabilize, or for some other reason
		valid = False
		# print(traceback.format_exc())
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
	return fitness


def frams_crossover(frams_lib: FramsticksLib, individual1, individual2):
	geno1 = individual1[0]  # individual[0] because we can't (?) have a simple str as a DEAP genotype/individual, only list of str.
	geno2 = individual2[0]  # individual[0] because we can't (?) have a simple str as a DEAP genotype/individual, only list of str.
	individual1[0] = frams_lib.crossOver(geno1, geno2)
	individual2[0] = frams_lib.crossOver(geno1, geno2)
	return individual1, individual2

def frams_dissim(frams_lib: FramsticksLib, individuals: list, dissim_method:DissimMethod):
	# FramsLib expect list of strings, not list of deap.creator.Individual
	ind_genos = [g[0] for g in individuals]
	return frams_lib.dissimilarity(ind_genos, method=dissim_method)


def frams_mutate(frams_lib: FramsticksLib, individual):
	individual[0] = frams_lib.mutate([individual[0]])[0]  # individual[0] because we can't (?) have a simple str as a DEAP genotype/individual, only list of str.
	return individual,


def frams_getsimplest(frams_lib: FramsticksLib, genetic_format, initial_genotype):
	return initial_genotype if initial_genotype is not None else frams_lib.getSimplest(genetic_format)

def frams_getrandomindividual(frams_lib: FramsticksLib, initial_genotype):
	ind = frams_lib.getRandomGenotype(initial_genotype, 2, 100, 2, 100, 100, True)
	print(ind)
	return ind


# from ..framspy import frams

# def get_numparts(frams_lib, genotype):
# 	m = frams.Model.newFromString(genotype)
# 	numparts = m.numparts._value()
# 	numneurons = m.numneurons._value()
# 	print("dir(Model)", dir(m))
# 	return {"numparts": numparts, "numneurons": numneurons}

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


def prepareToolbox(frams_lib, OPTIMIZATION_CRITERIA, tournament_size, genetic_format, initial_genotype) -> base.Toolbox:
	creator.create("FitnessMax", base.Fitness, weights=[1.0] * len(OPTIMIZATION_CRITERIA))
	creator.create("Individual", list, fitness=creator.FitnessMax)  # would be nice to have "str" instead of unnecessary "list of str"

	toolbox = base.Toolbox()
	toolbox.register("attr_simplest_genotype", frams_getsimplest, frams_lib, genetic_format, initial_genotype)  # "Attribute generator"
	toolbox.register("attr_random_genotype", frams_getrandomindividual, frams_lib, toolbox.attr_simplest_genotype())  # "Attribute generator"
	# (failed) struggle to have an individual which is a simple str, not a list of str
	# toolbox.register("individual", tools.initRepeat, creator.Individual, toolbox.attr_frams)
	# https://stackoverflow.com/questions/51451815/python-deap-library-using-random-words-as-individuals
	# https://github.com/DEAP/deap/issues/339
	# https://gitlab.com/santiagoandre/deap-customize-population-example/-/blob/master/AGbasic.py
	# https://groups.google.com/forum/#!topic/deap-users/22g1kyrpKy8
	toolbox.register("individual", tools.initRepeat, creator.Individual, toolbox.attr_simplest_genotype, 1)
	toolbox.register("random_individual", tools.initRepeat, creator.Individual, toolbox.attr_random_genotype, 1) # TODO: 
	# framsLib.getRandomGenotype(simplest, 2, 6, 2, 4, 100, True)
	# print(toolbox.individual())
	# print(toolbox.individual().fitness) ()
	# print(toolbox.individual().fitness.values) ()
	# exit(0)
	toolbox.register("population", tools.initRepeat, list, toolbox.individual)
	toolbox.register("evaluate", frams_evaluate, frams_lib)
	toolbox.register("mate", frams_crossover, frams_lib)
	toolbox.register("mutate", frams_mutate, frams_lib)
	toolbox.register("dissimilarity", frams_dissim, frams_lib) # Open the door to dissimilarity-based methods. FIXME: Does this count as an evaluation? I hope not...
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
	parser.add_argument('-evalfn', default=3, help="The fitness function to use. Values: 3 (default), 4, or 5")

	parser.add_argument('-genformat', required=False, help='Genetic format for the simplest initial genotype, for example 4, 9, or B. If not given, f1 is assumed.')
	parser.add_argument('-initialgenotype', required=False, help='The genotype used to seed the initial population. If given, the -genformat argument is ignored.')
	parser.add_argument('-skipinitialgenotype', type=int, default=0, help='If 1, set the fitness of the simplest genotype to 0.0, without evaluating it. Should slightly increase the amount of evaluated genotypes')

	parser.add_argument('-algorithm', required=True, choices=[
		'eaSimple', 'eaOnePlusLambdaLambda', 'eaMuPlusLambda', 'eaMuCommaLambda',
		'AdaptMut', 'convection_AdaptMut', 'convection_eaSimple',
		'NEAT_speciation'], help='The algorithm used in the run.')
	parser.add_argument('-nislands', type=int, default=10, help="Number of islands (only for convection), default: 10.")
	parser.add_argument('-island_eval_order', type=str, default='worstToBest', help="Order in which to evaluate islands (only for convection), could lead to minor performance boost for the last generation only, default: worstToBest")
	parser.add_argument('-migrate_after', type=int, default=10, help="Number of generations to execute for each island before migrating all islands (only for convection), default: 10.")
	parser.add_argument('-xmut_enabled', type=bool, default=1, help="0/1 If to enable mutation = replace with simple individual (only for AdaptMut), default: 1.")
	parser.add_argument('-added_ind', choices=['random', 'initial'], default='initial', help="(only for AdaptMut), what genotype to add with a low probability when mutating, default: initial.")
	parser.add_argument('-lbda', type=int, default=100, help="lambda - how many children to produce (only used for eaMuLambda), default: 100.") # Suggested: 7 * popsize (=350, but that seems like a bit much)
	parser.add_argument('-delta', type=float, default=3.0, help="delta (speciation) - Distance threshold for determining species.")
	parser.add_argument('-delta_under_mult', type=float, default=0.96, help="delta (speciation) - By how much to reduce the Distance threshold if the amount of species is too low.")
	parser.add_argument('-delta_over_mult', type=float, default=1.33, help="delta (speciation) - By how much to reduce the Distance threshold if the amount of species is too high.")
	parser.add_argument('-dissim', type=str, default="PHENE_STRUCT_OPTIM", help="dissimilarity method  (only used for ???), default: FITNESS.")

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
	exec(f"parsed_args.dissim = DissimMethod.{parsed_args.dissim}")
	if parsed_args.algorithm == 'eaOnePlusLambdaLambda' and parsed_args.popsize != 1:
		print(f"Error: You used the eaOnePlusLambdaLambda algorithm, but popsize is not 1 (it's {parsed_args.popsize})")
		exit(0)
	return parsed_args


def ensureDir(string):
	if os.path.isdir(string):
		return string
	else:
		raise NotADirectoryError(string)


def save_genotypes(filename, OPTIMIZATION_CRITERIA, hof):
	from ..framspy.framsfiles import writer as framswriter
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
	parsed_args = parseArguments()

	# random.seed(123)  # see FramsticksLib.DETERMINISTIC below, set to True if you want full determinism
	FramsticksLib.DETERMINISTIC = False  # must be set before the FramsticksLib() constructor call
	FramsticksLibCompetition.TEST_FUNCTION = int(parsed_args.evalfn)
	print("Argument values:", ", ".join(['%s=%s' % (arg, getattr(parsed_args, arg)) for arg in vars(parsed_args)]))
	OPTIMIZATION_CRITERIA = parsed_args.opt.split(",")
	framsLib = FramsticksLibCompetition(parsed_args.path, parsed_args.lib, parsed_args.sim)
	# if parsed_args.initialgenotype and parsed_args.skipinitialgenotype:
	# 	parsed_args.initialgenotype.fitness = DeapFitness()
	toolbox = prepareToolbox(framsLib, OPTIMIZATION_CRITERIA, parsed_args.tournament, '1' if parsed_args.genformat is None else parsed_args.genformat, parsed_args.initialgenotype)
	pop = toolbox.population(n=parsed_args.popsize)
	hof = tools.HallOfFame(parsed_args.hof_size)
	stats = tools.Statistics(lambda ind: ind.fitness.values)
	# calculate statistics excluding infeasible solutions (by filtering out those with fitness containing FITNESS_VALUE_INFEASIBLE_SOLUTION)
	filter_feasible_for_function = lambda function, fitness_criteria: (
		function(list(filter(is_feasible_fitness_criteria, fitness_criteria)))
		if any(is_feasible_fitness_criteria(fc) for fc in fitness_criteria)
		else float('nan')
	)
	stats.register("avg", lambda fitness_criteria: filter_feasible_for_function(np.mean, fitness_criteria))
	stats.register("stddev", lambda fitness_criteria: filter_feasible_for_function(np.std, fitness_criteria))
	stats.register("min", lambda fitness_criteria: filter_feasible_for_function(np.min, fitness_criteria))
	stats.register("max", lambda fitness_criteria: filter_feasible_for_function(np.max, fitness_criteria))
	stats.register("totalevals", lambda _: framsLib._evaluation_count)
	stats.register("evalTime", lambda _: framsLib._evaluation_time)
	stats.register("noneval_Time", lambda _: time.perf_counter() - framsLib._time0 - framsLib._evaluation_time)
	print('Max evals set to:', FramsticksLibCompetition.MAX_EVALUATIONS)
	print('Max time set to:', FramsticksLibCompetition.MAX_TIME)
	try:
		match parsed_args.algorithm:
			case "AdaptMut":
				print('am')
				from .dalgorithm.AdaptMut import adaptMut
				pop, log = adaptMut(
							pop, toolbox,
							cxpb=parsed_args.pxov, mutpb=parsed_args.pmut, ngen=parsed_args.generations, xmut_enabled=parsed_args.xmut_enabled,
							added_ind=parsed_args.added_ind,
							stats=stats, halloffame=hof, verbose=True)
			case "eaMuPlusLambda":
				print('eaMu+Lambda')
				pop, log = algorithms.eaMuPlusLambda(
							pop, toolbox, mu=len(pop), lambda_=parsed_args.lbda,
							cxpb=parsed_args.pxov, mutpb=parsed_args.pmut, ngen=parsed_args.generations,
							stats=stats, halloffame=hof, verbose=True)
			case "eaMuCommaLambda":
				print('eaMu,Lambda')
				pop, log = algorithms.eaMuCommaLambda(
							pop, toolbox, mu=len(pop), lambda_=parsed_args.lbda,
							cxpb=parsed_args.pxov, mutpb=parsed_args.pmut, ngen=parsed_args.generations,
							stats=stats, halloffame=hof, verbose=True)
			case "eaOnePlusLambdaLambda":
				print('ea1+(Lambda,Lambda)')
				from .dalgorithm.eaOnePlusLambdaLambda import eaOnePlusLambdaLambda
				pop, log = eaOnePlusLambdaLambda(
							pop, toolbox, lbda=parsed_args.lbda, ngen=parsed_args.generations,
							stats=stats, halloffame=hof, verbose=True)
			case "eaSimple":
				print('ea')
				pop, log = algorithms.eaSimple(
							pop, toolbox,
							cxpb=parsed_args.pxov, mutpb=parsed_args.pmut, ngen=parsed_args.generations,
							stats=stats, halloffame=hof, verbose=True)
			case "convection_eaSimple":
				print('cv_ea')
				def algo_ea(population, toolbox, **params):
					return algorithms.eaSimple(
						population, toolbox, ngen=params['generations'],
						cxpb=parsed_args.pxov, mutpb=parsed_args.pmut,
						stats=stats, halloffame=hof, verbose=True)

				from .dalgorithm.ConvectionSelection import convectionSelection, ConvectionSelectionPopulationEvalOrder
				match parsed_args.island_eval_order:
					case 'worstToBest':
						parsed_args.island_eval_order = ConvectionSelectionPopulationEvalOrder.WORST_TO_BEST
					case 'bestToWorst':
						parsed_args.island_eval_order = ConvectionSelectionPopulationEvalOrder.WORST_TO_BEST
					case 'interleaved':
						parsed_args.island_eval_order = ConvectionSelectionPopulationEvalOrder.INTERLEAVED
					case _:
						print("Unknown island evaluation order: ", parsed_args.island_eval_order)
						exit(0)
				pop, log = convectionSelection(pop, toolbox, ngen=parsed_args.generations,
								n_islands=parsed_args.nislands, reconvene_gen_interval=parsed_args.migrate_after, algo=algo_ea, island_eval_order=parsed_args.island_eval_order,
								stats=stats, halloffame=hof, verbose=True)
			case "convection_AdaptMut":
				print('cv_am')
				from .dalgorithm.AdaptMut import adaptMut
				def algo_am(population, toolbox, **params):
					return adaptMut(
						population, toolbox, ngen=params['generations'],
						cxpb=parsed_args.pxov, mutpb=parsed_args.pmut, xmut_enabled=parsed_args.xmut_enabled,
						added_ind=parsed_args.added_ind,
						stats=stats, halloffame=hof, verbose=True)

				from .dalgorithm.ConvectionSelection import convectionSelection, ConvectionSelectionPopulationEvalOrder
				match parsed_args.island_eval_order:
					case 'worstToBest':
						parsed_args.island_eval_order = ConvectionSelectionPopulationEvalOrder.WORST_TO_BEST
					case 'bestToWorst':
						parsed_args.island_eval_order = ConvectionSelectionPopulationEvalOrder.BEST_TO_WORST
					case 'interleaved':
						parsed_args.island_eval_order = ConvectionSelectionPopulationEvalOrder.INTERLEAVED
					case _:
						print("Unknown island evaluation order: ", parsed_args.island_eval_order)
						exit(0)
				pop, log = convectionSelection(pop, toolbox, ngen=parsed_args.generations,
								n_islands=parsed_args.nislands, reconvene_gen_interval=parsed_args.migrate_after, algo=algo_am, island_eval_order=parsed_args.island_eval_order,
								stats=stats, halloffame=hof, verbose=True)
			case "NEAT_speciation":
				print("NEATsp")
				from .dalgorithm.NEAT_speciation import speciation
				pop, log = speciation(pop, toolbox, ngen=parsed_args.generations,
						n_species=parsed_args.nislands, admission_delta=parsed_args.delta,
						dynamic_delta_under=parsed_args.delta_under_mult,
						dynamic_delta_over=parsed_args.delta_over_mult,
						cxpb=parsed_args.pxov, mutpb=parsed_args.pmut, dissimilarity_metric=parsed_args.dissim,
						stats=stats, halloffame=hof, verbose=True)
			case _:
				raise "Unknown algorithm"
	except EOFError:
		# Algorithm ended
		pass
	print('Best individuals:')
	for ind in hof:
		print(ind.fitness, '\t<--\t', ind[0])
	if parsed_args.hof_savefile is not None:
		save_genotypes(parsed_args.hof_savefile, OPTIMIZATION_CRITERIA, hof) # saves a *.gen file, convenient for loading into Framsticks. Otherwise, you can save the HOF in any file format you need.


if __name__ == "__main__":
	import time
	t0 = time.perf_counter()
	t0rt = time.time()
	main()
	total_time = time.perf_counter() - t0
	total_time_rt = time.time() - t0rt
	import psutil
	usedMemoryMBvms = psutil.Process().memory_info().vms / (1024 * 1024)
	usedMemoryMBrss = psutil.Process().memory_info().rss / (1024 * 1024)
	memoryBudgetMB = 2 * 1024
	print(f"RAM used (vms): {usedMemoryMBvms:.5f} MB / {memoryBudgetMB} MB ({usedMemoryMBvms/memoryBudgetMB * 100:.2f}% used)")
	print(f"RAM used (rss): {usedMemoryMBrss:.5f} MB / {memoryBudgetMB} MB ({usedMemoryMBrss/memoryBudgetMB * 100:.2f}% used)")
	print(f"Time taken (perf_counter): {total_time}")
	print(f"Real Time taken (time):    {total_time_rt} seconds")
