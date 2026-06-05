import pandas as pd
import time
from framspy.FramsticksLibCompetition import FramsticksLibCompetition
from ..dalgorithm.customMutation import CmutFramsLibReference, setExpProperty, getExpProperty, get_applied_mutation, get_all_prop_names, getExpProperty
import copy, random
import json, math
import numpy as np

EPS = 1e-20

SCORE_FNS = {
	'pos': lambda r: r['pos'], # Give more weight to operations which cause the most fitness increase
	'ratio': lambda r: r['pos']/(-r['neg']+EPS), # Give more weight to operations which cause most good when compared to harm
	# TODO: Why does this ('neg') give the best results? It makes no sense.
	# * Is risk seeking behavior better, because it encourages exploration more??
	# * The biggest 'pos' is not that strongly related to 'neg', so why is 'neg' so much better than pos?
	'neg': lambda r: r['neg'], # Give more weight to operations which cause the biggest fitness decrease
	'neg_conservative': lambda r: 0.999**(-r['neg']), # Give more weight to operations which cause the least fitness decrease (+-2%, so not wide swings)
	'const': lambda r: 1, # Maybe no bias is better?
	# The '2' below is a scaling factor I added on a whim, so the weights are more biased towards the wanted ratio. I don't think it's optimal necessarily, but it looks good in the first ~20 generations.
	'ratio_fifthrule': lambda r: 2 * (0.05 ** abs(1/5 - r['countpos']/(r['countneg'] + r['countpos'] + EPS))), # Give priority to operators which have a 1/5 ratio of good/bad fitness delta (counts)
	'ratio_v2': lambda r: (r['countpos']/(r['countneg'] + r['countpos'] + EPS)), # Give priority to operators which have a better ratio of good/(good+bad) fitness delta (counts)
}

class FramsticksLibCompetitionWithHistory(FramsticksLibCompetition):
	"""
	Custom wrapper which adds some data tracking. Keeps track of all generated individuals over the course of a run.
	"""

	def __init__(self, frams_path, frams_lib_name, sim_settings_files, frams_module,
					cacheActive=False, score_fn='ratio', genformat='0',
					decay=0.985, # Should forget deltas after ~500 evaluations, aka. 50 ind x 10 generations (but it can differ by algorithm)
					norm_method='mean',
					ESalgo='freqWindow',
				):
		super().__init__(frams_path, frams_lib_name, sim_settings_files)
		self.ESalgo = ESalgo
		self.genformat = genformat
		self.norm_method = norm_method
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
		self.decay = decay
		print('ignored_operation_types', CmutFramsLibReference.ignored_operation_types)
		## Hardcoded setting, so we can retrieve the mutation type that was applied.
		setExpProperty('gen_extmutinfo', 2)
		self.cacheActive = cacheActive
		print('cacheActive:', cacheActive)
		self.df = pd.DataFrame({
			'meta_evaluation_number': pd.Series(dtype='int'),
			# 'meta_timestamp': pd.Series(dtype='float'),
			# 'meta_generation': pd.Series(dtype='int'),
			# 'meta_algorithm': pd.Series(dtype='str'),
			# 'algo_data': pd.Series(dtype='object'),
			'geno_genotype_representation': pd.Series(dtype='str'),
			'geno_numparts': pd.Series(dtype='int'),
			'geno_numjoints': pd.Series(dtype='int'),
			'geno_numneurons': pd.Series(dtype='int'),
			'geno_numconnections': pd.Series(dtype='int'),
			# 'eval_raw': pd.Series(dtype='object'), # This consumes A LOT of memory
			'eval_fit': pd.Series(dtype='object'),
			# 'eval_time': pd.Series(dtype='float'),
			# 'eval_vertpos': pd.Series(dtype='float'),
			# 'eval_velocity': pd.Series(dtype='float'),
			# 'eval_distance': pd.Series(dtype='float'),
			# 'eval_COGpath': pd.Series(dtype='float'),
		})
		self.cmaes_store = {
			pname: {'pos': 0.0, 'neg': 0.0, 'countpos': 0, 'countneg':0} for pname in get_all_prop_names(genformat)
		}
		# It's technically not a mutation type yet. FIXME
		# if 'crossover' not in CmutFramsLibReference.ignored_operation_types:
		self.cmaes_store['crossover'] = {'pos': 0.0, 'neg': 0.0, 'countpos': 0, 'countneg':0}
		self.cmaes_store['invalid'] = {'pos': 0.0, 'neg': 0.0, 'countpos': 0, 'countneg':0}
		self.applied_operations = [] # To store the mutation types that were applied.
		self.score_fn = SCORE_FNS[score_fn]
		self.last_hash = None
		print('recorded', list(self.cmaes_store.keys()))

	def end(self):
		pd.set_option('display.max_columns', None)
		pd.set_option('display.max_colwidth', None)
		pd.set_option('display.max_rows', None)
		pd.set_option("display.width", None)
		if self.cacheActive:
			print(self.df)
		print(self.cmaes_store)
		return super().end()
	
	def mutate(self, genotype_list: list[str]) -> list[str]:
		# Store what mutations were applied to a genotype.
		"""
		Copied from `FramsticksLib.py`
		Returns:
			The genotype(s) of the mutated source genotype(s). self.GENOTYPE_INVALID for genotypes whose mutation failed (for example because the source genotype was invalid).
		"""
		assert isinstance(genotype_list, list)  # because in python, str has similar capabilities to a list and here it would pretend to work too, so to avoid any ambiguity
		self.set_mutation_simulation_params(self.score_fn, genotype_list.es_params if 'es_params' in dir(genotype_list) else dict())
		h = hash(json.dumps(self.cmaes_store, sort_keys=True))
		if h != self.last_hash:
			self.last_hash = hash(json.dumps(self.cmaes_store, sort_keys=True))
			TERMINAL_WIDTH = 203
			print(('~' * TERMINAL_WIDTH))
			print(' Mutation rates for this generation '.center(TERMINAL_WIDTH, '~'))
			for i, k in enumerate(sorted(list(self.cmaes_store.keys()))):
				print(f"{k:>10} - {f'{(getExpProperty(k)*100) if k not in CmutFramsLibReference.ignored_operation_types else -1:.2f}':>8} % (pos: {self.cmaes_store[k]['pos']:8.2f};  neg {self.cmaes_store[k]['neg']:8.2f}; cpos: {self.cmaes_store[k]['countpos']:8.2f}; cneg: {self.cmaes_store[k]['countneg']:8.2f}; rc: {self.cmaes_store[k]['countpos']/(self.cmaes_store[k]['countpos'] + self.cmaes_store[k]['countneg'] + EPS):8.2f})", end='\n' if i % 2 == 2 - 1 else ' | ')
			print('\n' + ('~' * TERMINAL_WIDTH))
		mutated = []
		frams = CmutFramsLibReference.custom_mut_frams_lib_reference # Added for python relative import reasons
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
	
	def crossOver(self, genotype_parent1, genotype_parent2):
		"""
		Copied from `FramsticksLib.py`
		Returns:
			The genotype of the offspring. self.GENOTYPE_INVALID if the crossing over failed.
		"""
		frams = CmutFramsLibReference.custom_mut_frams_lib_reference # Added for python relative import reasons
		offspring = frams.GenMan.crossOver(frams.Geno.newFromString(genotype_parent1), frams.Geno.newFromString(genotype_parent2))
		offspring_genotype = offspring.genotype._string()
		if offspring_genotype == self.GENOTYPE_INVALID and self.GENOTYPE_INVALID_OFFSPRING_SUBSTITUTE_ORIGINAL:
			print('[WARN] crossOver(%s, %s) failed but you requested GENOTYPE_INVALID_OFFSPRING_SUBSTITUTE_ORIGINAL, so returning a random parent instead. Reason for failure: %s' % (self.shortGenotype(genotype_parent1), self.shortGenotype(genotype_parent2), offspring.info._string()))
			offspring_genotype = random.choice([genotype_parent1, genotype_parent2])
		self.applied_operations += [get_applied_mutation(offspring)] # This was changed from the original implementation.
		return offspring_genotype

	def get_last_performed_operations(self):
		"""
		Returns the last mutations which were applied to genotypes (in order), and then removes the internally stored mutations, to prepare for the next mutation batch.
		"""
		r = self.applied_operations
		# Map the raw info strings to the operations ids I defined (the different mutation types, like `f0_j_stf` or `f0_n_new`)
		self.applied_operations = []
		return r

	def get_model_parts_dict(self, genotype: str):
		model = CmutFramsLibReference.custom_mut_frams_lib_reference.Model.newFromString(genotype)
		return {
				"geno_numparts": model.numparts._value(),
				"geno_numjoints": model.numjoints._value(),
				"geno_numneurons": model.numneurons._value(),
				"geno_numconnections": model.numconnections._value(),
		}

	def getCached(self, genotype: str):
		cached_row = self.df[self.df['geno_genotype_representation'] == genotype]
		if cached_row.empty:
			return None
		assert cached_row.iloc[0]['eval_fit'] != None, "Error, cached eval_raw is already None"
		return cached_row.iloc[0]

	def updateCached(self, genotype: str, **updates):
		"""
		Update one or more columns in the cached row for a genotype.
		"""
		if not self.cacheActive:
			return
		cached_row = self.df[self.df['geno_genotype_representation'] == genotype]
		if cached_row.empty:
			print("Error: ", genotype, "does not exist in cache.")
			exit(-1)
			return
			# new_record = {"geno_genotype_representation": genotype}
			# new_record.update(updates)
			# self.df = self.df._append(new_record, ignore_index=True)
			# return self.df.iloc[-1]

		idx = cached_row.index[0]
		for key, value in updates.items():
			self.df.at[idx, key] = value
			if key == 'eval_fit':
				# Update the mutation fitness increase?
				pass
		return# self.df.loc[idx]

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
			case 'freqWindowHard':
				raise NotImplementedError('freqWindowHard')
			# 	# Have a fixed window size, TODO: Somehow...
			# 	old_fitness = [individual.past_fitness] if isinstance(individual.past_fitness, float) else individual.past_fitness
			# 	fitness_delta = float(new_fitness[0] - old_fitness[0])
			# 	fitness_delta_type = 'neg' if fitness_delta < 0 else 'pos'
			# 	for op_type in individual.past_operations:
			# 		if op_type in self.cmaes_store.keys():
			# 			self.cmaes_store[op_type]['pos'] = self.decay * self.cmaes_store[op_type]['pos']
			# 			self.cmaes_store[op_type]['neg'] = self.decay * self.cmaes_store[op_type]['neg']
			# 			self.cmaes_store[op_type][fitness_delta_type] += (fitness_delta / len(individual.past_operations)) * individual.past_operations.count(op_type)
			# 			self.cmaes_store[op_type]['count' + fitness_delta_type] += individual.past_operations.count(op_type) / len(individual.past_operations)
			case 'cmaes':
				raise NotImplementedError('cmaes')
			# 	"""
			# 	Get the sum of one-hot vectors representing the past operations.
			# 	"""
			# 	old_fitness = [individual.past_fitness] if isinstance(individual.past_fitness, float) else individual.past_fitness
			# 	fitness_delta = float(new_fitness[0] - old_fitness[0])
			# 	# Have a canonical ordering of the operation types
			# 	orderedNames = sorted(self.cmaes_store.keys())
			# 	v = [individual.past_operations.count(op_type) * fitness_delta for op_type in orderedNames]
			# 	# actualCMAES(v)
			# 	# FIXME: I need to get the concept of a generation to be accessible down here.
			# 	pass

	def set_mutation_simulation_params(self, score_fn, paramsDict = dict()):
		"""
		In accordance to the CMA-ES collected statistics, update the mutation weights.
		Should have a mechanism to prevent feedback loops (aka. clamp the probabilities to be > 0)
		"""
		match self.ESalgo:
			case 'freqWindow':
				scores = [(k, score_fn(self.cmaes_store[k])) for k in self.cmaes_store.keys() if k not in CmutFramsLibReference.ignored_operation_types]
				scores_only = list(map(lambda x: x[1], scores))
				mean_score = sum(scores_only) / len(scores)
				if mean_score == 0:
					# First generation, so do nothing.
					return
				match self.norm_method:
					case 'mean':
						NORM_FACTOR = mean_score
					case 'mean100':
						NORM_FACTOR = mean_score / 100
					case 'eps':
						NORM_FACTOR = EPS
					case 'none':
						NORM_FACTOR = 0
				sum_scores = sum(scores_only) + NORM_FACTOR * len(scores)
				for k, score in scores:
					# Anti feedback loop mechansim, so no mutation type goes entirely extinct.
					score = (score + NORM_FACTOR) / sum_scores
					# Framsticks should auto-normalize the mutation probabilities, so don't normalize them here.
					setExpProperty(k, score)
			case 'cmaes':
				raise NotImplementedError('cmaes')
			case 'indstore':
				# Mutation rates are stored on the individual
				if len(paramsDict) > 0: # FIXME: This seems brittle
					s = sum(paramsDict['rates'].values()) + EPS
					for k in paramsDict['rates']:
						# Framsticks should auto-normalize the mutation probabilities, but normalize them here for pretty printing.
						paramsDict['rates'][k] = paramsDict['rates'][k] / s
						setExpProperty(k, paramsDict['rates'][k])
					print('ind.es_params(rates, steps) = ', paramsDict['rates'], paramsDict['steps'])
			case 'none':
				pass


	def _evaluate_single_genotype(self, genotype: str):
		if self.cacheActive:
			new_record = {
				"meta_evaluation_number": self._evaluation_count, # N-th evaluation sent to the FramSticks simulator
				# "meta_timestamp": time.ctime(), # When the evaluation took place.
				# "meta_generation": 1, # What generation the evaluation belongs to
				# "meta_algorithm": "1", # Dummy
				# "algo_data": {"1":"1"}, # Extra data for custom usecases
				"geno_genotype_representation": genotype, # String representation of the genotype
				"eval_fit": None,
				# "geno_numparts": 1,
				# "geno_numjoints": 1,
				# "geno_numneurons": 1,
				# "geno_numconnections": 1,
				# "eval_raw": ret, # Fallback for raw output, in case of errors # This consumes A LOT of memory
				# "eval_time": 1.0,
				# "eval_vertpos": 1.0,
				# "eval_velocity": 1.0,
				# "eval_distance": 1.0,
				# "eval_COGpath": 1.0,
			}
			new_record.update(self.get_model_parts_dict(genotype))
		# Idk about this one, I need to determine an acceptible similarity threshold for cached_geno ~~ genotype
		# THIS WAS MOVED TO runExperiment.PY, DON'T UNCOMMENT IT UNLESS IT'S AN EMERGENCY.
		# if self.cacheActive and self.getCached(genotype) is not None and self.getCached(genotype)['eval_fit'] is not None:
		# 	print(f"Using cached value for <{genotype[:25].replace('\n', '\\n')}>")
		# 	return self.getCached(genotype)['eval_fit']
		ret = super()._evaluate_single_genotype(genotype)
		# new_record["eval_raw"] = ret
		if self.cacheActive:
			self.df = self.df._append(new_record, ignore_index=True)
		# print("df len:", self.df.shape, genotype[:25].replace('\n', '\\n'))
		return ret