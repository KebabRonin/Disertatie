import pandas as pd
import time
from framspy.FramsticksLibCompetition import FramsticksLibCompetition

class FramsticksLibCompetitionWithHistory(FramsticksLibCompetition):
	"""
	Custom wrapper which adds some data tracking. Keeps track of all generated individuals over the course of a run.
	"""

	def __init__(self, frams_path, frams_lib_name, sim_settings_files):
		super().__init__(frams_path, frams_lib_name, sim_settings_files)
		self.df = pd.DataFrame({
			'meta_evaluation_number': pd.Series(dtype='int'),
			'meta_timestamp': pd.Series(dtype='float'),
			'meta_generation': pd.Series(dtype='int'),
			'meta_algorithm': pd.Series(dtype='str'),
			'algo_data': pd.Series(dtype='object'),
			'geno_genotype_representation': pd.Series(dtype='str'),
			'geno_numparts': pd.Series(dtype='int'),
			'geno_numjoints': pd.Series(dtype='int'),
			'geno_numneurons': pd.Series(dtype='int'),
			'geno_numconnections': pd.Series(dtype='int'),
			'eval_raw': pd.Series(dtype='str'),
			'eval_time': pd.Series(dtype='float'),
			'eval_vertpos': pd.Series(dtype='float'),
			'eval_velocity': pd.Series(dtype='float'),
			'eval_distance': pd.Series(dtype='float'),
			'eval_COGpath': pd.Series(dtype='float'),
		})

	def end():
		return super().end()


	def _evaluate_single_genotype(self, genotype):
		new_record = {
			"meta_evaluation_number": self._evaluation_count, # N-th evaluation sent to the FramSticks simulator
			"meta_timestamp": time.time(), # When the evaluation took place.
			"meta_generation": 1, # What generation the evaluation belongs to
			"meta_algorithm": "1", # Dummy
			"algo_data": {"1":"1"},
			"geno_genotype_representation": "1", # String representation of the genotype
			"geno_numparts": 1,
			"geno_numjoints": 1,
			"geno_numneurons": 1,
			"geno_numconnections": 1,
			"eval_raw": "1", # Fallback for raw output, in case of errors
			"eval_time": 1.0,
			"eval_vertpos": 1.0,
			"eval_velocity": 1.0,
			"eval_distance": 1.0,
			"eval_COGpath": 1.0,
		}
		print(dir(genotype))
		# Idk about this one, I need to determine an acceptible similarity threshold for cached_geno ~~ genotype
		# if self.cacheActive and self.hasCached(genotype):
		# 	return self.getCached(genotype)
		ret = super()._evaluate_single_genotype(genotype)
		self.df = self.df._append(new_record, ignore_index=True)
		return ret