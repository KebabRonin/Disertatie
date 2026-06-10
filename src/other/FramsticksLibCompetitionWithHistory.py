import pandas as pd
import time
from FramsticksLibCompetition import FramsticksLibCompetition
from ..dalgorithm.customMutation import CmutFramsLibReference, setExpProperty, getExpProperty, get_applied_mutation, get_all_prop_names, getExpProperty
import copy, random
import json, math
import numpy as np

EPS = 1e-20

class FramsticksLibCompetitionWithHistory(FramsticksLibCompetition):
	"""
	Custom wrapper which adds some data tracking. Keeps track of all generated individuals over the course of a run.
	"""

	def __init__(self, frams_path, frams_lib_name, sim_settings_files, frams_module, genformat='0',
					ESalgo='freqWindow',
				):
		super().__init__(frams_path, frams_lib_name, sim_settings_files)
		self.ESalgo = ESalgo
		self.genformat = genformat
		CmutFramsLibReference.custom_mut_frams_lib_reference = frams_module
		# Ignore some genetic operations for CMA-ES, based on the current simulator settings
		CmutFramsLibReference.ignored_operation_types += [
			p for p in get_all_prop_names(genformat) if getExpProperty(p) == 0
		]
		CmutFramsLibReference.ignored_operation_types += [
			'crossover', 'invalid',
			'f0_nodel_tag', 'f0_nomod_tag',
			'f1_xo_propor',
			]
		self.decay = 0.985
		print('ignored_operation_types', CmutFramsLibReference.ignored_operation_types)
		## Hardcoded setting, so we can retrieve the mutation type that was applied.
		setExpProperty('gen_extmutinfo', 2)
		self.cmaes_store = {
			pname: {'pos': 0.0, 'neg': 0.0, 'countpos': 0, 'countneg':0} for pname in get_all_prop_names(genformat)
		}
		# It's technically not a mutation type yet. FIXME
		# if 'crossover' not in CmutFramsLibReference.ignored_operation_types:
		self.cmaes_store['crossover'] = {'pos': 0.0, 'neg': 0.0, 'countpos': 0, 'countneg':0}
		self.cmaes_store['invalid'] = {'pos': 0.0, 'neg': 0.0, 'countpos': 0, 'countneg':0}
		self.applied_operations = [] # To store the mutation types that were applied.
		self.score_fn = lambda r: r['neg']
		self.last_hash = None
		print('recorded', list(self.cmaes_store.keys()))

	def end(self):
		print(self.cmaes_store)
		return super().end()
	
	def print_mutation_probs(self):
		TERMINAL_WIDTH = 217
		print(('~' * TERMINAL_WIDTH))
		print(' Mutation rates for this generation '.center(TERMINAL_WIDTH, '~'))
		for i, k in enumerate(sorted(list(self.cmaes_store.keys()))):
			print(f"{k:>10} - {f'{(getExpProperty(k)*100) if k not in CmutFramsLibReference.ignored_operation_types else -1:.2f}':>8} % (pos: {self.cmaes_store[k]['pos']:8.2f};  neg {self.cmaes_store[k]['neg']:15.2f}; cpos: {self.cmaes_store[k]['countpos']:8.2f}; cneg: {self.cmaes_store[k]['countneg']:8.2f}; rc: {self.cmaes_store[k]['countpos']/(self.cmaes_store[k]['countpos'] + self.cmaes_store[k]['countneg'] + EPS):8.2f})", end='\n' if i % 2 == 2 - 1 else ' | ')
		print('\n' + ('~' * TERMINAL_WIDTH))
	
	def mutate(self, genotype_list: list[str]) -> list[str]:
		# Store what mutations were applied to a genotype.
		"""
		Copied from `FramsticksLib.py`
		Returns:
			The genotype(s) of the mutated source genotype(s). self.GENOTYPE_INVALID for genotypes whose mutation failed (for example because the source genotype was invalid).
		"""
		assert isinstance(genotype_list, list)  # because in python, str has similar capabilities to a list and here it would pretend to work too, so to avoid any ambiguity

		self.set_mutation_simulation_params()
		h = hash(json.dumps(self.cmaes_store, sort_keys=True))
		if h != self.last_hash:
			self.last_hash = hash(json.dumps(self.cmaes_store, sort_keys=True))
			self.print_mutation_probs()
		frams = CmutFramsLibReference.custom_mut_frams_lib_reference # Added for python relative import reasons
		mutated = []
		for genotype_parent in genotype_list:
			offspring = frams.GenMan.mutate(frams.Geno.newFromString(genotype_parent))
			offspring_genotype = offspring.genotype._string()
			if offspring_genotype == self.GENOTYPE_INVALID and self.GENOTYPE_INVALID_OFFSPRING_SUBSTITUTE_ORIGINAL:
				print('[WARN] mutate(%s) failed but you requested GENOTYPE_INVALID_OFFSPRING_SUBSTITUTE_ORIGINAL, so returning the original genotype instead. Reason for failure: %s' % (self.shortGenotype(genotype_parent), offspring.info._string()))
				offspring_genotype = genotype_parent
			self.applied_operations += [get_applied_mutation(offspring)] # This was changed from the original implementation.
			mutated.append(offspring_genotype)
		if len(genotype_list) != len(mutated):
			raise RuntimeError("Submitted %d genotypes, received %d mutants" % (len(genotype_list), len(mutated)))
		return mutated

	def get_last_performed_operations(self):
		"""
		Returns the last mutations which were applied to genotypes (in order), and then removes the internally stored mutations, to prepare for the next mutation batch.
		"""
		r = self.applied_operations
		# Map the raw info strings to the operations ids I defined (the different mutation types, like `f0_j_stf` or `f0_n_new`)
		self.applied_operations = []
		return r

	def updateMutationStatistics(self, individual, new_fitness):
		"""
		This is called on every evaluate() call, to consume the operation history stored on each genotype.

		Update the "CMA-ES"-like history of the impact of each operation type.
		This initial implementation is as follows:
		* Keep a rolling sum over each operation type (eg. 'f0_n_new': [sum_fit_improvement_deltas, sum_fit_worse_deltas] )
		* If n operations were applied, contribute 1/n to each operation's sum
		* Later on, you this dict can be used to compute the simulation parameters for each operation
		"""
		# FIXME: Uncomment this and fix it if you want to support multiple fitness values. I'm good for now.
		# if isinstance(individual.past_fitness, float):
		# 	# Uninitialized past fitness
		# 	individual.past_fitness = [0.0 for _ in range(len(new_fitness))]
		match self.ESalgo:
			case 'freqWindow':
				if new_fitness[0] == -999999.0: # FIXME: This should be FITNESS_VALUE_INFEASIBLE_SOLUTION instead.
					# Don't count invalid individuals.
					# This is mainly to avoid a feedback loop for AdaptMut with neg score_fn and max_numparts 3 , so f0_p_add isn't promoted into oblivion and you end up with an all-infeasible population.
					return
				# Soft window by using decay
				old_fitness = [individual.past_fitness] if isinstance(individual.past_fitness, float) else individual.past_fitness
				fitness_delta = float(new_fitness[0] - old_fitness[0])
				fitness_delta_type = 'neg' if fitness_delta < 0 else 'pos'
				for op_type in individual.past_operations:
					if op_type in self.cmaes_store.keys():
						self.cmaes_store[op_type]['pos'] = self.decay * self.cmaes_store[op_type]['pos']
						self.cmaes_store[op_type]['neg'] = self.decay * self.cmaes_store[op_type]['neg']
						self.cmaes_store[op_type][fitness_delta_type] += (fitness_delta / len(individual.past_operations)) * individual.past_operations.count(op_type)
						self.cmaes_store[op_type]['count' + fitness_delta_type] += individual.past_operations.count(op_type) / len(individual.past_operations)
			case 'none':
				pass

	def set_mutation_simulation_params(self):
		"""
		In accordance to the CMA-ES collected statistics, update the mutation weights.
		Should have a mechanism to prevent feedback loops (aka. clamp the probabilities to be > 0)
		"""
		match self.ESalgo:
			case 'freqWindow':
				scores = [(k, self.score_fn(self.cmaes_store[k])) for k in self.cmaes_store.keys() if k not in CmutFramsLibReference.ignored_operation_types]
				scores_only = list(map(lambda x: x[1], scores))
				mean_score = sum(scores_only) / len(scores)
				if mean_score == 0:
					# First generation, so do nothing.
					return
				NORM_FACTOR = mean_score
				sum_scores = sum(scores_only) + NORM_FACTOR * len(scores)
				for k, score in scores:
					# Anti feedback loop mechansim, so no mutation type goes entirely extinct.
					score = (score + NORM_FACTOR) / sum_scores
					# Framsticks should auto-normalize the mutation probabilities, so don't normalize them here.
					setExpProperty(k, score)
			case 'none':
				pass