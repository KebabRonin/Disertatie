import random
import numpy as np
import math
from deap import tools, creator
from FramsticksLib import FramsticksLib
import json # For printing only
import random
import frams

FITNESS_VALUE_INFEASIBLE_SOLUTION = -999999.0
EPS = 1e-20
printextra = print
## <Marker> If you want to disable the mutation strength, restart window and mutation prob console output, uncomment this line:
# printextra = lambda *x, **kx: 0

"""
(Ctrl+F for `<Marker>` to see code structure headings)
<Marker> Moved here from customMutation.py
"""
MUT_PARAMS = {
  "0":  {
# Mutation weights pertaining to body parts/joints,
    "f0_p_new": 5.0,
    "f0_p_del": 5.0,
    "f0_p_swp": 10.0,
    "f0_p_pos": 10.0,
    "f0_p_den": 0.0,
    "f0_p_frc": 10.0,
    "f0_p_ing": 10.0,
    "f0_p_asm": 0.0,
    "f0_p_color": 0.0,
    "f0_j_new": 5.0,
    "f0_j_del": 5.0,
    "f0_j_stm": 0.0,
    "f0_j_stf": 10.0,
    "f0_j_rsf": 10.0,
    "f0_j_color": 0.0,
# ??? Idk how to add tags,
    "f0_nodel_tag": 1,
    "f0_nomod_tag": 1,
# Mutation weights pertaining to neurons/neuron connections,
    "f0_n_new": 5.0,
    "f0_n_del": 5.0,
    "f0_n_prp": 10.0,
    "f0_c_new": 5.0,
    "f0_c_del": 5.0,
    "f0_c_wei": 10.0,
  },
  "1":  {
    # Body
    # "f1_smModifiers": "LlRrCcQqFfMm",
    "f1_smX": 0.05,
    "f1_smJunct": 0.02,
    "f1_smComma": 0.02,
    "f1_smModif": 0.1,
    # Brain
    # "f1_xo_propor": 1, # point crossover will cut so the same amount of neurons is in both cut parts
    "f1_nmNeu": 0.05,
    "f1_nmConn": 0.1,
    "f1_nmProp": 0.1,
    "f1_nmWei": 1.0,
    "f1_nmVal": 0.05,
  },
}

INFO_MUT = {
  '0':{
    "added Neuron": "f0_n_new",
    "changed Neuron property": "f0_n_prp",
    "removed Neuron": "f0_n_del",
    "added neural connection": "f0_c_new",
    "changed neural connection weight": "f0_c_wei",
    "removed neural connection": "f0_c_del",
    "added Joint": "f0_j_new",
    "changed Joint color": "f0_j_color",
    "changed Joint stamina": "f0_j_stm",
    "changed Joint stiffness": "f0_j_stf",
    "changed Joint rotational stiffness": "f0_j_rsf",
    "removed Joint": "f0_j_del",
    "added Part": "f0_p_new",
    "changed Part density": "f0_p_den",
    "changed Part ingestion": "f0_p_ing",
    "changed Part friction": "f0_p_frc",
    "changed Part assimilation": "f0_p_asm",
    "changed Part position": "f0_p_pos",
    "changed Part color": "f0_p_color",
    "swapped Part": "f0_p_swp",
    "removed Part": "f0_p_del",
  },
  '1': {
    "added or removed a neuron": "f1_nmNeu",
    "added or removed neuron property": "f1_nmProp",
    "changed neuron property": "f1_nmVal",
    "added or removed neural connection": "f1_nmConn",
    "changed neural connection weight": "f1_nmWei",
    "added or removed a modifier": "f1_smModif",
    "added or removed a comma": "f1_smComma",
    "added or removed X": "f1_smX",
    "added or removed branching": "f1_smJunct",
  }
}

import re
MUTATION_INFO_RE = re.compile(r'mutation\((.*?)\)')
def get_applied_mutation(offspring) -> str:
  """
  Get the type of mutation that was last applied to this genotype.
  Requires frams.GenMan.gen_extmutinfo = 2 to be set.
  """
  assert getExpProperty('gen_extmutinfo') == 2, getExpProperty('gen_extmutinfo')
  s = str(offspring.info)
  m = re.search(MUTATION_INFO_RE, s)
  if not m:
    if not re.search('Crossing over of ', s):
      print('Unknown operation type:', s, 'ooo')
      return 'invalid'
    return 'crossover'
  mutation_match = m.group(1)
  if mutation_match not in INFO_MUT[offspring.format._value()]:
    print('Unknown mutation type:', mutation_match, 'eee')
    return 'invalid'
  return INFO_MUT[offspring.format._value()][mutation_match]

mutator_ignored_operation_types = []

def setExpProperty(name, value):
  setattr(frams.GenMan, name, value)
  assert getExpProperty(name) == value

def getExpProperty(name):
  return getattr(frams.GenMan, name)._value()

def get_all_prop_names(genetic_repr = None):
  global mutator_ignored_operation_types
  names = list(MUT_PARAMS["0"].keys() if genetic_repr != '1' else []) + list(MUT_PARAMS["1"].keys() if genetic_repr != '0' else [])
  return list(set(filter(lambda x: x not in mutator_ignored_operation_types, names)))

"""
<Marker> Moved here from wHist
"""

def print_mutation_probs(cmaes_store):
	TERMINAL_WIDTH = 217
	printextra(('~' * TERMINAL_WIDTH))
	printextra(' Mutation rates for this generation '.center(TERMINAL_WIDTH, '~'))
	for i, k in enumerate(sorted(list(cmaes_store.keys()))):
		printextra(f"{k:>10} - {f'{(getExpProperty(k)*100) if k not in mutator_ignored_operation_types else -1:.2f}':>8} % (pos: {cmaes_store[k]['pos']:8.2f};  neg {cmaes_store[k]['neg']:15.2f}; cpos: {cmaes_store[k]['countpos']:8.2f}; cneg: {cmaes_store[k]['countneg']:8.2f}; rc: {cmaes_store[k]['countpos']/(cmaes_store[k]['countpos'] + cmaes_store[k]['countneg'] + EPS):8.2f})", end='\n' if i % 2 == 2 - 1 else ' | ')
	printextra('\n' + ('~' * TERMINAL_WIDTH))


class Mutator:
	"""
	Stores mutation rates, and handles mutating genotypes.
	"""
	def __init__(self):
		global mutator_ignored_operation_types
		# Ignore some genetic operations for CMA-ES, based on the current simulator settings
		mutator_ignored_operation_types += [
			p for p in get_all_prop_names() if getExpProperty(p) == 0
		]
		mutator_ignored_operation_types += [
			'crossover', 'invalid',
			'f0_nodel_tag', 'f0_nomod_tag',
			'f1_xo_propor',
			]
		self.decay = 0.985
		printextra('ignored_operation_types', mutator_ignored_operation_types)
		self.cmaes_store = {
			pname: {'pos': 0.0, 'neg': 0.0, 'countpos': 0, 'countneg':0} for pname in get_all_prop_names()
		}
		self.applied_operations = [] # To store the mutation types that were applied.
		self.score_fn = lambda r: r['neg']
		self.last_hash = None
		printextra('recorded', list(self.cmaes_store.keys()))

	
	def custom_mutate(self, individual: creator.Individual) -> creator.Individual:
		# Store what mutations were applied to a genotype.
		"""
		Copied from `FramsticksLib.py`
		Returns:
			The genotype(s) of the mutated source genotype(s). self.GENOTYPE_INVALID for genotypes whose mutation failed (for example because the source genotype was invalid).
		"""
		mutation_simulation_params_probs = self.get_mutation_simulation_params()
		for k in mutation_simulation_params_probs.keys():
			setExpProperty(k, mutation_simulation_params_probs[k])
			# print(getExpProperty(k))
		h = hash(json.dumps(self.cmaes_store, sort_keys=True))
		if h != self.last_hash:
			self.last_hash = hash(json.dumps(self.cmaes_store, sort_keys=True))
			print_mutation_probs(self.cmaes_store)
		offspring = frams.GenMan.mutate(frams.Geno.newFromString(individual[0]))
		if offspring.genotype._string() == FramsticksLib.GENOTYPE_INVALID and FramsticksLib.GENOTYPE_INVALID_OFFSPRING_SUBSTITUTE_ORIGINAL:
			print('[WARN] mutate(%s) failed but you requested GENOTYPE_INVALID_OFFSPRING_SUBSTITUTE_ORIGINAL, so returning the original genotype instead. Reason for failure: %s' % (FramsticksLib.shortGenotype(individual), offspring.info._string()))
			offspring = individual
		else:
			offspring_new = creator.Individual([offspring.genotype._string()])
			setattr(offspring_new, 'past_operations', getattr(individual, 'past_operations', []) + [get_applied_mutation(offspring)])
			setattr(offspring_new, 'past_fitness', getattr(individual, 'past_fitness', [0.0]))
			offspring = offspring_new
		return offspring,

	def updateMutationStatistics(self, individual, new_fitness):
		"""
		This is called on every evaluate() call, to consume the operation history stored on each genotype.

		Update the "CMA-ES"-like history of the impact of each operation type.
		This initial implementation is as follows:
		* Keep a rolling sum over each operation type (eg. 'f0_n_new': [sum_fit_improvement_deltas, sum_fit_worse_deltas] )
		* If n operations were applied, contribute 1/n to each operation's sum
		* Later on, you this dict can be used to compute the simulation parameters for each operation
		"""
		if new_fitness[0] == FITNESS_VALUE_INFEASIBLE_SOLUTION: # FIXME: This should be FITNESS_VALUE_INFEASIBLE_SOLUTION instead.
			# Don't count invalid individuals.
			# This is mainly to avoid a feedback loop for AdaptMut with neg score_fn and max_numparts 3 , so f0_p_add isn't promoted into oblivion and you end up with an all-infeasible population.
			return
		# Soft window by using decay
		fness = getattr(individual, 'past_fitness', 0.0)
		old_fitness = [0.0] if fness == 0.0 else fness
		fitness_delta = float(new_fitness[0] - old_fitness[0])
		fitness_delta_type = 'neg' if fitness_delta < 0 else 'pos'
		pastops = getattr(individual, 'past_operations', [])
		for op_type in pastops:
			if op_type in self.cmaes_store.keys():
				self.cmaes_store[op_type]['pos'] = self.decay * self.cmaes_store[op_type]['pos']
				self.cmaes_store[op_type]['neg'] = self.decay * self.cmaes_store[op_type]['neg']
				self.cmaes_store[op_type][fitness_delta_type] += (fitness_delta / len(pastops)) * pastops.count(op_type)
				self.cmaes_store[op_type]['count' + fitness_delta_type] += pastops.count(op_type) / len(pastops)

	def get_mutation_simulation_params(self):
		"""
		In accordance to the CMA-ES collected statistics, update the mutation weights.
		Should have a mechanism to prevent feedback loops (aka. clamp the probabilities to be > 0)
		"""
		scores = [(k, self.score_fn(self.cmaes_store[k])) for k in self.cmaes_store.keys() if k not in mutator_ignored_operation_types]
		# for s in scores:
		# 	print(str(s)[:25])
		scores_only = list(map(lambda x: x[1], scores))
		mean_score = sum(scores_only) / len(scores)
		if mean_score == 0:
			# First generation, so do nothing.
			return dict()
		NORM_FACTOR = mean_score
		d = dict()
		sum_scores = sum(scores_only) + NORM_FACTOR * len(scores)
		for k, score in scores:
			# Anti feedback loop mechansim, so no mutation type goes entirely extinct.
			score = (score + NORM_FACTOR) / sum_scores
			d[k] = score
			# setExpProperty(k, score)
		return d

"""
<Marker> Moved from runExperiment.py (setting up and function definitions)
"""
mutator = Mutator()


def custom_Eval(frams_lib: FramsticksLib, toolbox, individual):
	global mutator
	FITNESS_CRITERIA_INFEASIBLE_SOLUTION = [FITNESS_VALUE_INFEASIBLE_SOLUTION]  # this special fitness value indicates that the solution should not be propagated via selection ("that genotype is invalid"). The floating point value is only used for compatibility with DEAP. If you implement your own optimization algorithm, instead of a negative value in this constant, use a special value like None to properly distinguish between feasible and infeasible solutions.
	if not frams_lib.isValidCreature([individual[0]])[0]:
		# Short circuit if invalid genotype.
		# printextra('Skippin\' invalid creature.')
		return FITNESS_CRITERIA_INFEASIBLE_SOLUTION
	# real eval
	fitness = toolbox.evaluate(individual)
	# Update mutation operation frequency statistics
	mutator.updateMutationStatistics(individual, fitness)
	setattr(individual, 'past_fitness', fitness)
	setattr(individual, 'past_operations', [])
	return fitness

def attr_random_pop_from_genotype(frams_lib, max_numparts, max_numneurons, toolbox, init_geno, n, ratio=0.25):
	"""
	Generate a new population by perturbing the given genotype. For use in soft_perturb_best restart method.
	"""
	pop = [tools.initRepeat(creator.Individual, lambda: frams_lib.getRandomGenotype(init_geno,
			2,
				min(max_numparts if max_numparts is not None else 10000000000000000000, 100),
			# Movement should require at least 2 neurons: A muscle and a sensor
			min(max_numneurons if max_numneurons is not None else 10000000000000000000, 2),
				min(max_numneurons if max_numneurons is not None else 10000000000000000000, 100),
			random.randrange(0, 4), True)
		, 1) for _ in range(int(n * ratio))]
	# Reinit with 1/4(bestratio) best ind, 3/4 randoms.
	return pop + [tools.initRepeat(creator.Individual, toolbox.attr_random_genotype, 1) for _ in range(n - len(pop))]

def frams_getrandomindividual(frams_lib: FramsticksLib, max_numparts, max_numneurons, initial_genotype):
	ind = frams_lib.getRandomGenotype(initial_genotype, 
			2,
				min(max_numparts if max_numparts is not None else 10000000000000000000, 100),
			# Movement should require at least 2 neurons: A muscle and a sensor
			min(max_numneurons if max_numneurons is not None else 10000000000000000000, 2),
				min(max_numneurons if max_numneurons is not None else 10000000000000000000, 100),
			100, True)
	return ind

def init(frams_lib, toolbox, max_numparts, max_numneurons):
	setExpProperty('gen_extmutinfo', 2) # Force the simulator to record what mutation was applied
	toolbox.register("attr_random_genotype", frams_getrandomindividual, frams_lib, max_numparts, max_numneurons, toolbox.attr_simplest_genotype())  # "Attribute generator"
	toolbox.register("attr_random_pop_from_genotype", attr_random_pop_from_genotype, frams_lib, max_numparts, max_numneurons, toolbox)  # "Attribute generator"
	toolbox.register("random_individual", tools.initRepeat, creator.Individual, toolbox.attr_random_genotype, 1) # TODO: 
	toolbox.register("population", tools.initRepeat, list, toolbox.random_individual)
	toolbox.register("custom_Eval", custom_Eval, frams_lib, toolbox)

"""
<Marker> Actual algo code
"""

def s_int(x):
	"""Stochastic rounding"""
	a = math.floor(x)
	b = a + 1
	return (np.random.choice([a, b], p=[b - x, x - a]))

def varAnd(population, toolbox, cxpb, mutpb, mutstrength):
	r"""
	This variation is named *And* because of its propensity to apply both
	crossover and mutation on the individuals. Note that both operators are
	not applied systematically, the resulting individuals can be generated from
	crossover only, mutation only, crossover and mutation, and reproduction
	according to the given probabilities. Both probabilities should be in
	:math:`[0, 1]`.
	"""
	offspring = [toolbox.clone(ind) for ind in population]

	# Apply crossover and mutation on the offspring
	for i in range(1, len(offspring), 2):
		if random.random() < cxpb:
			offspring[i - 1], offspring[i] = toolbox.mate(offspring[i - 1],
														  offspring[i])
			del offspring[i - 1].fitness.values, offspring[i].fitness.values

	for i in range(len(offspring)):
		nr_mutations = s_int(mutstrength)
		for j in range(nr_mutations):
			if random.random() < mutpb:
				if random.random() < 0.01:
					## AdaptMut randomly adds a RANDOM specimen rarely
					offspring[i] = toolbox.random_individual()
				else:
					offspring[i], = mutator.custom_mutate(offspring[i])
					del offspring[i].fitness.values
	return offspring

def dynMut(population, toolbox, cxpb, mutpb, ngen, framsLib, max_numparts, max_numneurons,
			restart_patience,
			stats=None, halloffame=None, verbose=__debug__):
	# Augument the toolbox with some extra tools, for generating random individuals.
	init(framsLib, toolbox, max_numparts, max_numneurons)
	"""
	Taken from deap, adapted for adaptMut
	"""
	logbook = tools.Logbook()
	logbook.header = ['gen', 'nevals'] + (stats.fields if stats else [])

	# First step: Get a more random population from the initial one.
	population = toolbox.attr_random_pop_from_genotype(population[0][0], len(population), ratio=0)

	# Evaluate the individuals with an invalid fitness
	invalid_ind = [ind for ind in population if not ind.fitness.valid]
	fitnesses = toolbox.map(toolbox.custom_Eval, invalid_ind)
	for ind, fit in zip(invalid_ind, fitnesses):
		ind.fitness.values = fit

	if halloffame is not None:
		halloffame.update(population)

	record = stats.compile(population) if stats else {}
	logbook.record(gen=0, nevals=len(invalid_ind), **record)
	if verbose:
		print(logbook.stream)

	mutationStrength = 1.0
	maxFits = []
	bestFitPastAll = (float('-inf'), [''])

	# Begin the generational process
	for gen in range(1, ngen + 1):
		# Select the next generation individuals
		offspring = toolbox.select(population, len(population))
		# Vary the pool of individuals
		offspring = varAnd(offspring, toolbox, cxpb, mutpb, mutationStrength)

		# for p in offspring:
		# 	print(f"{str(p)[:25]:<25} {getattr(p, 'past_operations', [])}")
		# Evaluate the individuals with an invalid fitness
		invalid_ind = [ind for ind in offspring if not ind.fitness.valid]
		fitnesses = toolbox.map(toolbox.custom_Eval, invalid_ind)

		# Only takes into account newly generated individuals. Old folks who persisted unchanged don't contribute to the history.
		maxFit = (float('-inf'), [''])
		for ind, fit in zip(invalid_ind, fitnesses):
			ind.fitness.values = fit
			if fit[0] > maxFit[0]:
				maxFit = (fit[0], toolbox.clone(ind))
		if maxFit[0] != float('-inf'):
			maxFits.append(maxFit)

		# Update the hall of fame with the generated individuals
		if halloffame is not None:
			halloffame.update(offspring)

		# Replace the current population by the offspring
		population[:] = offspring

		# Append the current generation statistics to the logbook
		record = stats.compile(population) if stats else {}
		logbook.record(gen=gen, nevals=len(invalid_ind), **record)
		if verbose:
			print(logbook.stream)

		if len(maxFits) > 4:
			bestFitPastConsider = maxFits[-5]
			if maxFit[0] - bestFitPastConsider[0] < 0.01 * bestFitPastConsider[0]:
				mutationStrength *= 1.1
			else:
				mutationStrength *= 0.9
			mutationStrength = float(np.clip(mutationStrength, 1.0, 5.0))
			printextra("New mutation strength:", mutationStrength)

		if len(maxFits) >= restart_patience:
			consider_interval = maxFits[-restart_patience:-1]
			bestFitPast = sorted(consider_interval, key=lambda x: x[0], reverse=True)[0]
			bestFitPastAllConsider = sorted(maxFits, key=lambda x: x[0], reverse=True)[0]
			bestFitPastAll = bestFitPastAllConsider if bestFitPastAllConsider > bestFitPastAll else bestFitPastAll
			ind = consider_interval.index(bestFitPast)
			printextra(f"Best past: {bestFitPast[0]:20.5f} | Best in patience window: {maxFits[-1][0]:20.5f} | Patience: {ind} / {restart_patience}")
			if maxFits[-1][0] <= bestFitPast[0] and ind == 0:
				printextra("Restarting...")
				population = toolbox.attr_random_pop_from_genotype(bestFitPast[1][0], len(population))

				# Evaluate the individuals with an invalid fitness
				invalid_ind = [ind for ind in population if not ind.fitness.valid]
				fitnesses = toolbox.map(toolbox.custom_Eval, invalid_ind)
				for ind, fit in zip(invalid_ind, fitnesses):
					ind.fitness.values = fit

				if halloffame is not None:
					halloffame.update(population)

				record = stats.compile(population) if stats else {}
				logbook.record(gen=f"{gen}.restarting", nevals=len(invalid_ind), **record)
				if verbose:
					print(logbook.stream)
				
				maxFits = []

	return population, logbook