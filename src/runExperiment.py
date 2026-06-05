import random
import argparse
import os
import sys
import numpy as np
from deap import creator, base, tools, algorithms
from .config_loader import get_framspy_path
sys.path.append(get_framspy_path()) # FIXME: Needed so `import frams` from files in framspy are imported correctly (i.e. FramsticksLib)
from framspy.FramsticksLib import FramsticksLib, DissimMethod
from framspy.FramsticksLibCompetition import FramsticksLibCompetition
import traceback
import frams
from scipy.spatial import distance
# Note: this may be less efficient than running the evolution directly in Framsticks, so if performance is key, compare both options.

from .other.FramsticksLibCompetitionWithHistory import FramsticksLibCompetitionWithHistory

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

def frams_compute_crowding_distance(frams_lib, dissim_method, population: list[list[str]], distance_matrix=None):
	"""
	Compute a crowding distance for a population.
	Updates the population individuals inplace, and returns the computed distance matrix, for reuse in whatever you need.

	Should be called after evaluating the population, so we can compute the 'FITNESS' dissim method.
	FIXME: CONTRADICTION: This is part of the fitness.
	"""
	return None # This was a valiant attempt, but I won't use it.
	try:
		crowding_idx_in_fitness = OPTIMIZATION_CRITERIA.index('crowding')
	except ValueError:
		# No crowding needed
		return None
	
	if distance_matrix is None:
		distance_matrix = frams_dissim(frams_lib, population, dissim_method)
	print(distance_matrix)

	popaddrs = [id(geno) for geno in population]
	for geno in population:
		idx = popaddrs.index(id(geno))
		if geno.fitness.valid:
				# Add the crowding distance as an evaluated fitness metric, if a dissim method was defined, by replacing the fitness altogether.
				geno.fitness.values = tuple(np.linalg.norm(distance_matrix[idx], ord=2) / 1_000_000 if indx == crowding_idx_in_fitness else geno.fitness.values[indx] for indx in range(len(geno.fitness.values)))
	return distance_matrix

def frams_evaluate(frams_lib, individual, population=None, dissim_method=DissimMethod.GENE_LEVENSHTEIN):
	FITNESS_CRITERIA_INFEASIBLE_SOLUTION = [FITNESS_VALUE_INFEASIBLE_SOLUTION] * len(OPTIMIZATION_CRITERIA)  # this special fitness value indicates that the solution should not be propagated via selection ("that genotype is invalid"). The floating point value is only used for compatibility with DEAP. If you implement your own optimization algorithm, instead of a negative value in this constant, use a special value like None to properly distinguish between feasible and infeasible solutions.
	if not frams_lib.isValidCreature([individual[0]])[0]:
		# Short circuit if invalid genotype.
		# individual.fitness.values = (FITNESS_CRITERIA_INFEASIBLE_SOLUTION,)
		return FITNESS_CRITERIA_INFEASIBLE_SOLUTION
	genotype = individual[0]  # individual[0] because we can't (?) have a simple str as a DEAP genotype/individual, only list of str.
	if isinstance(frams_lib, FramsticksLibCompetitionWithHistory) and frams_lib.getCached(genotype) is not None:
		assert frams_lib.getCached(genotype)['eval_fit'] is not None
		frams_lib.updateMutationStatistics(individual, frams_lib.getCached(genotype)['eval_fit'])
		individual.past_fitness = frams_lib.getCached(genotype)['eval_fit']
		individual.past_operations = []
		return frams_lib.getCached(genotype)['eval_fit']
	data = frams_lib.evaluate([genotype])
	# if population:
	# 	# For crowding distance, 
	# 	frams_compute_crowding_distance(frams_lib, dissim_method, population)
	# print("{'genotype': \"" + genotype.replace('\n', '\\n') + "\", 'data': " + str(data) + "}", file=sys.stderr)
	valid = True
	try:
		first_genotype_data = data[0]
		evaluation_data = first_genotype_data["evaluations"]
		default_evaluation_data = evaluation_data[""]
		default_evaluation_data['crowding'] = 0.0 # Placeholder so crowding distance can be computed separately for each generation, without consuming an evaluation.
		fitness = [default_evaluation_data[crit] for crit in OPTIMIZATION_CRITERIA]
	except (KeyError, TypeError) as e:  # the evaluation may have failed for an invalid genotype (such as X[@][@] with "Don't simulate genotypes with warnings" option), or because the creature failed to stabilize, or for some other reason
		valid = False
		print(traceback.format_exc())
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

def fix_geno(frams_lib: FramsticksLib, fix_invalid: str, individual: str) -> str:
	"""
		Given a genotype (str), get back a fixed str
	"""
	match fix_invalid:
		case 'mutate':
			nmaxmut = 100
			for _ in range(nmaxmut):
				if frams_lib.isValidCreature([individual])[0]:
					break
				individual = frams_lib.mutate([individual])[0]
			if not frams_lib.isValidCreature([individual])[0]:
				print(f"Failed to fix genotype after {nmaxmut} mutations: individual")
			return individual
		case _:
			return individual

def frams_crossover(frams_lib: FramsticksLib, individual1, individual2):
	# Do crossover for the mutation probabilities stored in `es_params`:
	# * Take a random choice from the parents
	# * Maybe also take the mean of the 2 parents? TODO
	assert individual1.es_params['rates'].keys() == individual2.es_params['rates'].keys() == individual1.es_params['steps'].keys() == individual2.es_params['steps'].keys()
	keys = individual1.es_params['rates'].keys()
	newrates1 = {'steps': {}, 'rates': {}}
	newrates2 = {'steps': {}, 'rates': {}}
	# print('xvp', str(individual1.es_params)[:250])
	# print('xvp', str(individual2.es_params)[:250])
	for k in keys:
		if parsed_args.xov_mutschema == 'rand':
			newrates1['rates'][k] = individual2.es_params['rates'][k] + random.random() * (individual1.es_params['rates'][k] - individual2.es_params['rates'][k])
			newrates2['rates'][k] = individual2.es_params['rates'][k] + random.random() * (individual1.es_params['rates'][k] - individual2.es_params['rates'][k])
			newrates1['steps'][k] = individual2.es_params['steps'][k] + random.random() * (individual1.es_params['steps'][k] - individual2.es_params['steps'][k])
			newrates2['steps'][k] = individual2.es_params['steps'][k] + random.random() * (individual1.es_params['steps'][k] - individual2.es_params['steps'][k])
		else: # choice
			newrates1['rates'][k] = random.choice([individual1.es_params['rates'][k], individual2.es_params['rates'][k]])
			newrates2['rates'][k] = random.choice([individual1.es_params['rates'][k], individual2.es_params['rates'][k]])
			newrates1['steps'][k] = random.choice([individual1.es_params['steps'][k], individual2.es_params['steps'][k]])
			newrates2['steps'][k] = random.choice([individual1.es_params['steps'][k], individual2.es_params['steps'][k]])
		# print(f"rates {float(individual1.es_params['rates'][k])} + {float(individual2.es_params['rates'][k])} -> ({float(newrates1['rates'][k])} {float(newrates2['rates'][k])})")
		# print(f"steps {float(individual1.es_params['steps'][k])} + {float(individual2.es_params['steps'][k])} -> ({float(newrates1['steps'][k])} {float(newrates2['steps'][k])})")
	individual1.es_params = newrates1
	individual2.es_params = newrates2
	# print('xvc', str(individual1.es_params)[:250])
	# print('xvc', str(individual2.es_params)[:250])
	geno1 = individual1[0]  # individual[0] because we can't (?) have a simple str as a DEAP genotype/individual, only list of str.
	geno2 = individual2[0]  # individual[0] because we can't (?) have a simple str as a DEAP genotype/individual, only list of str.
	individual1[0] = frams_lib.crossOver(geno1, geno2)
	individual1[0] = fix_geno(frams_lib, parsed_args.fix_invalid, individual1[0])
	if isinstance(frams_lib, FramsticksLibCompetitionWithHistory):
		individual1.past_operations += frams_lib.get_last_performed_operations()
	individual2[0] = frams_lib.crossOver(geno1, geno2)
	individual2[0] = fix_geno(frams_lib, parsed_args.fix_invalid, individual2[0])
	if isinstance(frams_lib, FramsticksLibCompetitionWithHistory):
		individual2.past_operations += frams_lib.get_last_performed_operations()
	return individual1, individual2

def frams_mutate(frams_lib: FramsticksLib, individual):
	# print('mut', str(individual.es_params)[:250])
	individual[0] = frams_lib.mutate(individual)[0]  # individual[0] because we can't (?) have a simple str as a DEAP genotype/individual, only list of str.
	individual[0] = fix_geno(frams_lib, parsed_args.fix_invalid, individual[0])
	# Mutate mutation rates:
	k2 = random.choice(list(individual.es_params['rates'].keys()))
	individual.es_params['rates'][k2] += random.normalvariate() * individual.es_params['steps'][k2]
	individual.es_params['rates'][k2] = float(np.clip(individual.es_params['rates'][k2], 1e-8, 1))
	individual.es_params['steps'][k2] += random.normalvariate() * 1e-2
	individual.es_params['steps'][k2] = float(np.clip(individual.es_params['steps'][k2], 1e-8, 1))
	if isinstance(frams_lib, FramsticksLibCompetitionWithHistory):
		individual.past_operations += frams_lib.get_last_performed_operations()
	return individual,

def fitness_dissim(individuals):
  n = len(individuals)

  fitnesses = np.array([ind.fitness.values for ind in individuals])
  square_matrix = distance.cdist(fitnesses,fitnesses, 'euclidean')
  assert square_matrix.shape == (n, n)

  return square_matrix

def frams_dissim(frams_lib: FramsticksLib, individuals: list, dissim_method:DissimMethod):
	# FramsLib expect list of strings, not list of deap.creator.Individual
	ind_genos = [g[0] for g in individuals]
	if dissim_method == DissimMethod.FITNESS:
		# Handle it here, since frams_lib doesn't implement it.
		return fitness_dissim(individuals)
	else:
		return frams_lib.dissimilarity(ind_genos, method=dissim_method)

def frams_isValid(frams_lib: FramsticksLib, individual):
	return frams_lib.isValid([individual[0]])[0]

def frams_isValidCreature(frams_lib: FramsticksLib, individual):
	return frams_lib.isValidCreature([individual[0]])[0]

def frams_getsimplest(frams_lib: FramsticksLib, genetic_format, initial_genotype):
	assert initial_genotype is None or frams.Geno.newFromString(initial_genotype).format._value() == genetic_format
	return initial_genotype if initial_genotype is not None else frams_lib.getSimplest(genetic_format)

def frams_getrandomindividual(frams_lib: FramsticksLib, initial_genotype):
	ind = frams_lib.getRandomGenotype(initial_genotype, 
			2,
				min(parsed_args.max_numparts if parsed_args.max_numparts is not None else 10000000000000000000, 100),
			# Movement should require at least 2 neurons: A muscle and a sensor
			min(parsed_args.max_numneurons if parsed_args.max_numneurons is not None else 10000000000000000000, 2),
				min(parsed_args.max_numneurons if parsed_args.max_numneurons is not None else 10000000000000000000, 100),
			100, True)
	return ind


# from framspy import frams

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

def selRoulette_only_feasible(individuals, k):
	feasible_individuals = select_feasible(individuals)
	if len(feasible_individuals) == 0:
		print("Selection: no feasible solution in the population of size %d, so selecting from all individuals (including infeasible solutions with special fitness value %s)" % (len(individuals), FITNESS_VALUE_INFEASIBLE_SOLUTION))
		return tools.selRoulette(individuals, k)
	return tools.selRoulette(feasible_individuals, k)

def selBest_only_feasible(individuals, k):
	feasible_individuals = select_feasible(individuals)
	if len(feasible_individuals) == 0:
		print("Selection: no feasible solution in the population of size %d, so selecting from all individuals (including infeasible solutions with special fitness value %s)" % (len(individuals), FITNESS_VALUE_INFEASIBLE_SOLUTION))
		return tools.selBest(individuals, k)
	return tools.selBest(feasible_individuals, k)

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

def prepareToolbox(frams_lib: FramsticksLib, OPTIMIZATION_CRITERIA, tournament_size, genetic_format, initial_genotype, dissim) -> base.Toolbox:
	creator.create("FitnessMax", base.Fitness, weights=[1.0] * len(OPTIMIZATION_CRITERIA))
	# Added:
	# * past_operations: A list of all genetic operations performed on this Individual since the last evaluation
	# * past_fitness: The result of the last evaluated parent of this Individual. It's a float just to have a
	# 		placeholder while the Individual has not been evaluated. Actual individuals should replace that float fitness
	# 		value with the a base.Fitness (aka. list[float])
	# * es_params: The mutation parameters stored on this individual. It's supposed to be for those mainly, but you can
	# 		store anything you want in it. It's your dict, do whatever.

	# would be nice to have "str" instead of unnecessary "list of str"
	# Actually: list is a nice stand-in for C pointers. Otherwise, trying to replace an individual's genotype would
	# replace the entire object pointer, thus losing the individual.
	creator.create("Individual", list, fitness=creator.FitnessMax,
			past_operations=list, past_fitness=float, es_params=dict)

	toolbox = base.Toolbox()
	toolbox.register("attr_simplest_genotype", frams_getsimplest, frams_lib, genetic_format, initial_genotype)  # "Attribute generator"
	toolbox.register("attr_random_genotype", frams_getrandomindividual, frams_lib, toolbox.attr_simplest_genotype())  # "Attribute generator"
	def attr_random_pop_from_genotype(frams_lib, init_geno, n):
		"""
		Generate a new population by perturbing the given genotype. For use in soft_perturb_best restart method.
		"""
		pop = [tools.initRepeat(creator.Individual, lambda: frams_lib.getRandomGenotype(init_geno,
				2,
					min(parsed_args.max_numparts if parsed_args.max_numparts is not None else 10000000000000000000, 100),
				# Movement should require at least 2 neurons: A muscle and a sensor
				min(parsed_args.max_numneurons if parsed_args.max_numneurons is not None else 10000000000000000000, 2),
					min(parsed_args.max_numneurons if parsed_args.max_numneurons is not None else 10000000000000000000, 100),
				random.randrange(0, parsed_args.softperturbbest_maxnewmutcount), True)
			, 1) for _ in range(int(n * parsed_args.softperturbbest_bestratio))]
		# Reinit with 1/4(bestratio) best ind, 3/4 randoms.
		return pop + [tools.initRepeat(creator.Individual, toolbox.attr_random_genotype, 1) for _ in range(n - len(pop))]

	toolbox.register("attr_random_pop_from_genotype", attr_random_pop_from_genotype, frams_lib)  # "Attribute generator"
	# (failed) struggle to have an individual which is a simple str, not a list of str
	# toolbox.register("individual", tools.initRepeat, creator.Individual, toolbox.attr_frams)
	# https://stackoverflow.com/questions/51451815/python-deap-library-using-random-words-as-individuals
	# https://github.com/DEAP/deap/issues/339
	# https://gitlab.com/santiagoandre/deap-customize-population-example/-/blob/master/AGbasic.py
	# https://groups.google.com/forum/#!topic/deap-users/22g1kyrpKy8
	from .dalgorithm.customMutation import get_all_prop_names
	def initInd(genotype):
		ind = creator.Individual(genotype)
		ind.es_params = {'steps': {}, 'rates': {}}
		pnames = get_all_prop_names(parsed_args.genformat)
		rates = np.random.random(len(pnames))
		steps = np.random.random(len(pnames))
		rates /= rates.sum()
		steps /= steps.sum()
		for i, k in enumerate(pnames):
			ind.es_params['rates'][k] = float(rates[i])
			ind.es_params['steps'][k] = float(steps[i])
		# print('gen', str(ind.es_params)[:250])
		return ind
	toolbox.register("individual", tools.initRepeat, initInd, toolbox.attr_simplest_genotype, 1)
	toolbox.register("individual_from_str", initInd)
	toolbox.register("random_individual", tools.initRepeat, initInd, toolbox.attr_random_genotype, 1) # TODO: 
	if parsed_args.population_initialization == 'random':
		toolbox.register("population", tools.initRepeat, list, toolbox.random_individual)
	elif parsed_args.population_initialization == 'clone':
		toolbox.register("population", tools.initRepeat, list, toolbox.individual)
	# if 'crowding' in parsed_args.opt:
	# 	toolbox.register("evaluate", frams_evaluate_with_crowding, frams_lib)
	# else:
	if isinstance(frams_lib, FramsticksLibCompetitionWithHistory) and frams_lib.cacheActive:
		toolbox.register("getArchive", lambda flib: flib.df, frams_lib)
	toolbox.register("isValid", frams_isValidCreature, frams_lib) # frams_isValidCreature frams_isValid
	toolbox.register("isValid", frams_isValidCreature, frams_lib) # frams_isValidCreature frams_isValid
	toolbox.register("evaluate", frams_evaluate, frams_lib)
	toolbox.register("add_crowding_distance", frams_compute_crowding_distance, frams_lib, dissim)
	toolbox.register("mate", frams_crossover, frams_lib)
	toolbox.register("mutate", frams_mutate, frams_lib)
	toolbox.register("dissimilarity", frams_dissim, frams_lib) # Open the door to dissimilarity-based methods. FIXME: Does this count as an evaluation? I hope not...
	if len(OPTIMIZATION_CRITERIA) <= 1:
		# toolbox.register("select", tools.selTournament, tournsize=tournament_size) # without explicitly filtering out infeasible solutions - eliminating/discriminating infeasible solutions during selection would only rely on their relatively poor fitness value
		match parsed_args.selMethod:
			case 'tournament':
				toolbox.register("select", selTournament_only_feasible, tournsize=tournament_size)
			case 'roulette':
				# THIS IS WRONG: If you start with initialgenotype = 'X' it breaks, since roulette of a population with 0 fitness makes no sense.
				toolbox.register("select", selRoulette_only_feasible)
			case 'best':
				toolbox.register("select", selBest_only_feasible)
			case _:
				print('[ERROR]: Unsupported selection type: ', parsed_args.selMethod)
				exit(1)
	else:
		# toolbox.register("select", selNSGA2) # without explicitly filtering out infeasible solutions - eliminating/discriminating infeasible solutions during selection would only rely on their relatively poor fitness value
		toolbox.register("select", selNSGA2_only_feasible, toolboxclone=toolbox.clone)
	return toolbox


def parseArguments():
	parser = argparse.ArgumentParser(description='Run this program with "python -u %s" if you want to disable buffering of its output.' % sys.argv[0])
	parser.add_argument('-path', type=ensureDir, required=True, help='Path to Framsticks library without trailing slash.')
	parser.add_argument('-framspath', type=ensureDir, required=False, help='Path to framspy folder without trailing slash.')
	parser.add_argument('-lib', required=False, help='Library name. If not given, "frams-objects.dll" (or .so or .dylib) is assumed depending on the platform.')
	parser.add_argument('-sim', required=False, default="eval-allcriteria.sim", help="The name of the .sim file with settings for evaluation, mutation, crossover, and similarity estimation. If not given, \"eval-allcriteria.sim\" is assumed by default. Must be compatible with the \"standard-eval\" expdef. If you want to provide more files, separate them with a semicolon ';'.")
	parser.add_argument('-evalfn', default=3, help="The fitness function to use. Values: 3 (default), 4, or 5")

	parser.add_argument('-genformat', required=False, help='Genetic format for the simplest initial genotype, for example 4, 9, or B. If not given, f1 is assumed.', default='1')
	parser.add_argument('-initialgenotype', required=False, help='The genotype used to seed the initial population. If given, the -genformat argument is ignored.')
	parser.add_argument('-skipinitialgenotype', type=int, default=0, help='If 1, set the fitness of the simplest genotype to 0.0, without evaluating it. Should slightly increase the amount of evaluated genotypes')

	parser.add_argument('-selMethod', choices=['tournament', 'roulette', 'best'], default='tournament')
	parser.add_argument('-flibclass', choices=['competition', 'wHist'], default='competition')
	parser.add_argument('-wHist_scorefn', required=False, choices=['ratio', 'pos', 'neg', 'neg_conservative', 'const', 'ratio_fifthrule', 'ratio_v2'], default='ratio')
	parser.add_argument('-wHist_decay', required=False, type=float, default=0.985)
	parser.add_argument('-wHist_norm_method', required=False, choices=['mean', 'mean100', 'none', 'eps'], default='mean')
	parser.add_argument('-wHist_cacheActive', required=False, default='0')
	parser.add_argument('-wHist_ESalgo', required=False, choices=['none', 'cmaes', 'freqWindow', 'indstore'], default='freqWindow')
	parser.add_argument('-algorithm', required=True, choices=[
		'eaSimple', 'eaOnePlusLambdaLambda', 'eaMuPlusLambda', 'eaMuCommaLambda',
		'AdaptMut', 'convection_AdaptMut', 'convection_eaSimple', 'Annealer',
		'RandomMutationCount', 'MAPElites',
		'NEAT_speciation'], help='The algorithm used in the run.')
	parser.add_argument('-nislands', type=int, default=10, help="Number of islands (only for convection), default: 10.")
	parser.add_argument('-island_eval_order', type=str, default='worstToBest', help="Order in which to evaluate islands (only for convection), could lead to minor performance boost for the last generation only, default: worstToBest")
	parser.add_argument('-migrate_after', type=int, default=10, help="Number of generations to execute for each island before migrating all islands (only for convection), default: 10.")
	parser.add_argument('-maxmutationsperstep', type=int, default=5, help="Number of mutations to perform when an individual is selected for mutation, default: 5.")
	parser.add_argument('-fix_invalid', choices=['none', 'mutate'], default='none', help="What to do with invalid solutions.")
	parser.add_argument('-xmut_enabled', type=bool, default=1, help="0/1 If to enable mutation = replace with simple individual (only for AdaptMut), default: 1.")
	parser.add_argument('-restart_patience', type=int, default=20, help=r"After how many generations of no improvement greater than 1% in the max fitness to do a restart.")
	parser.add_argument('-restart_method', choices=['hard', 'soft_perturb_best', 'soft_perturb_best_all', 'none'], default='none', help="Restart hard (so reinit pop from scratch), or soft (by applying some mutations to the best ind from the run that is ending and continuing the run)")
	parser.add_argument('-softperturbbest_bestratio', type=float, default=0.25, help=r"Restart soft perturb best will initialize the new population with this % best ind (mutated _ times), and the rest are random individuals")
	parser.add_argument('-softperturbbest_maxnewmutcount', type=int, default=4, help=r"Restart soft perturb best will initialize the new population with the best ind mutated at most this many times range(0, _)")
	parser.add_argument('-added_ind', choices=['random', 'initial'], default='initial', help="(only for AdaptMut), what genotype to add with a low probability when mutating, default: initial.")
	parser.add_argument('-lbda', type=int, default=100, help="lambda - how many children to produce (only used for eaMuLambda), default: 100.") # Suggested: 7 * popsize (=350, but that seems like a bit much)
	parser.add_argument('-delta', type=float, default=3.0, help="delta (speciation) - Distance threshold for determining species.")
	parser.add_argument('-delta_under_mult', type=float, default=0.96, help="delta (speciation) - By how much to reduce the Distance threshold if the amount of species is too low.")
	parser.add_argument('-delta_over_mult', type=float, default=1.33, help="delta (speciation) - By how much to reduce the Distance threshold if the amount of species is too high.")
	parser.add_argument('-dissim', type=str, default="PHENE_STRUCT_OPTIM", help="dissimilarity method  (only used for ???), default: PHENE_STRUCT_OPTIM.")

	parser.add_argument('-novelty_features', default=','.join(['geno_numparts', 'geno_numjoints', 'geno_numneurons', 'geno_numconnections']), help="Features to split the grid by in MAP-Elites (comma separated). Can contain any of: 'geno_numparts', 'geno_numjoints', 'geno_numneurons', 'geno_numconnections'")
	parser.add_argument('-novelty_sel', default='random', help="How to pick the next individual to evaluate") #, choices=['random']

	parser.add_argument('-opt', required=True, help='optimization criteria: vertpos, velocity, distance, vertvel, lifespan, numjoints, numparts, numneurons, numconnections (or other as long as it is provided by the .sim file and its .expdef). For multiple criteria optimization, separate the names by the comma.')
	parser.add_argument('-popsize', type=int, default=50, help="Population size, default: 50.")
	parser.add_argument('-generations', type=int, default=5, help="Number of generations, default: 5.")
	parser.add_argument('-tournament', type=int, default=5, help="Tournament size, default: 5.")
	parser.add_argument('-pmut', type=float, default=0.9, help="Probability of mutation, default: 0.9")
	parser.add_argument('-xov_mutschema', choices=['choice', 'rand'], default='choice', help="How to update the mutation params as part of the crossover operation, default: rand")
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
	if parsed_args.initialgenotype == 'random':
		parsed_args.population_initialization = 'random'
		parsed_args.initialgenotype = None
	else:
		parsed_args.population_initialization = 'clone'
	parsed_args.wHist_cacheActive = parsed_args.wHist_cacheActive != '0'
	return parsed_args


def ensureDir(string):
	if os.path.isdir(string):
		return string
	else:
		raise NotADirectoryError(string)


def save_genotypes(filename, OPTIMIZATION_CRITERIA, hof):
	from framspy.framsfiles import writer as framswriter
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
	match parsed_args.flibclass:
		case 'competition':
			framsLib = FramsticksLibCompetition(parsed_args.path, parsed_args.lib, parsed_args.sim)
		case 'wHist':
			# Also implements Evolutionary Strategy (remembers all past mutations, and adjusts weights)
			framsLib = FramsticksLibCompetitionWithHistory(
				parsed_args.path, parsed_args.lib, parsed_args.sim, frams,
				cacheActive=parsed_args.wHist_cacheActive, score_fn=parsed_args.wHist_scorefn, decay=parsed_args.wHist_decay,
				norm_method=parsed_args.wHist_norm_method, ESalgo=parsed_args.wHist_ESalgo,
			)
		case _:
			print("Unknown framslibclass", parsed_args.flibclass)
			exit(0)
	# if parsed_args.initialgenotype and parsed_args.skipinitialgenotype:
	# 	parsed_args.initialgenotype.fitness = DeapFitness()
	if len(OPTIMIZATION_CRITERIA) <= 1:
		print("Probably using regular selection")
	else:
		print("Probably using NSGA-II selection")
	toolbox = prepareToolbox(framsLib,
									OPTIMIZATION_CRITERIA,
									parsed_args.tournament, parsed_args.genformat,
									parsed_args.initialgenotype,
									parsed_args.dissim
									)
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
	stats.register("noneval_Time", lambda _: time.perf_counter() - framsLib._time0 - framsLib._evaluation_time)
	print('Max evals set to:', FramsticksLibCompetition.MAX_EVALUATIONS)
	print('Max time set to:', FramsticksLibCompetition.MAX_TIME)
	try:
		match parsed_args.algorithm:
			case "RandomMutationCount":
				print('jazz')
				from .dalgorithm.RandomMutationCount import randomMutationCount
				pop, log = randomMutationCount(
							pop, toolbox,
							maxmutationsperstep=parsed_args.maxmutationsperstep,
							cxpb=parsed_args.pxov, mutpb=parsed_args.pmut, ngen=parsed_args.generations,
							restart_method=parsed_args.restart_method, restart_patience=parsed_args.restart_patience,
							stats=stats, halloffame=hof, verbose=True)
			case "AdaptMut":
				print('am')
				from .dalgorithm.AdaptMut import adaptMut
				pop, log = adaptMut(
							pop, toolbox,
							cxpb=parsed_args.pxov, mutpb=parsed_args.pmut, ngen=parsed_args.generations, xmut_enabled=parsed_args.xmut_enabled,
							restart_method=parsed_args.restart_method, restart_patience=parsed_args.restart_patience,
							added_ind=parsed_args.added_ind,
							stats=stats, halloffame=hof, verbose=True)
			case "MAPElites":
				print('mapelites')
				from .dalgorithm.MAPElites import mapElites
				mapElites(
							pop, toolbox,
							cxpb=parsed_args.pxov, mutpb=parsed_args.pmut, ngen=parsed_args.generations,
							features=parsed_args.novelty_features.split(','),
							grid_selection_method=parsed_args.novelty_sel,
							topk=parsed_args.tournament,
							restart_method=parsed_args.restart_method, restart_patience=parsed_args.restart_patience,
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
							maxmutationsperstep=parsed_args.maxmutationsperstep,
							stats=stats, halloffame=hof, verbose=True)
			case "eaSimple":
				print('ea')
				pop, log = algorithms.eaSimple(
							pop, toolbox,
							cxpb=parsed_args.pxov, mutpb=parsed_args.pmut, ngen=parsed_args.generations,
							stats=stats, halloffame=hof, verbose=True)
			case "Annealer":
				print('Annealer')
				from .dalgorithm import Annealer
				pop, log = Annealer.annealer(
							pop, toolbox,
							ngen=parsed_args.generations,
							adaptMut=parsed_args.xmut_enabled,
							# adaptMutPatience=parsed_args.restart_patience,
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
								# restart_method=parsed_args.restart_method, restart_patience=parsed_args.restart_patience,
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
								# restart_method=parsed_args.restart_method, restart_patience=parsed_args.restart_patience,
								stats=stats, halloffame=hof, verbose=True)
			case "NEAT_speciation":
				print("NEATsp")
				from .dalgorithm.NEAT_speciation import speciation
				pop, log = speciation(pop, toolbox, ngen=parsed_args.generations,
						n_species=parsed_args.nislands, admission_delta=parsed_args.delta,
						dynamic_delta_under=parsed_args.delta_under_mult,
						dynamic_delta_over=parsed_args.delta_over_mult,
						cxpb=parsed_args.pxov, mutpb=parsed_args.pmut, dissimilarity_metric=parsed_args.dissim,
						restart_method=parsed_args.restart_method, restart_patience=parsed_args.restart_patience,
						stats=stats, halloffame=hof, verbose=True)
			case _:
				raise "Unknown algorithm"
	except EOFError:
		# Algorithm ended
		pass
	except KeyboardInterrupt:
		try:
			# End throws an EOFError to signal the end
			framsLib.end()
		except EOFError:
			# Algorithm ended
			pass
	print('Best individuals:')
	for ind in hof:
		print(ind.fitness, '\t<--\t', ind[0])
	if parsed_args.hof_savefile is not None:
		save_genotypes(parsed_args.hof_savefile, OPTIMIZATION_CRITERIA, hof) # saves a *.gen file, convenient for loading into Framsticks. Otherwise, you can save the HOF in any file format you need.
		if isinstance(framsLib, FramsticksLibCompetitionWithHistory) and framsLib.cacheActive:
			import re
			number = re.search(r"hof_(\d+)\.txt", parsed_args.hof_savefile)
			if number:
				number, = number.groups()
				framsLib.df.to_pickle(os.path.join(os.path.dirname(parsed_args.hof_savefile), f'framslib_history_cache_{number}.pkl'))


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
