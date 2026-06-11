## Installation Instructions

1. Unzip the attached archive
2. Copy `DynMut.py` and `runExperiment.py` into your framspy folder (which contains the `FramsticksLibCompetition.py` file)
3. (optional) Uncomment `printextra = lambda *x, **kx: 0` in `DynMut.py` to disable debug prints for restart, mutation strength, mutation probabilities
4. Run the following command:
```
python runExperiment -path <PATH_TO_FRAMSTICKS> -sim "eval-allcriteria.sim;deterministic.sim;recording-body-coords.sim" -opt COGpath -genformat 0 -pmut 0.8 -pxov 0.2 -popsize 50 -generations 1000000
```

## Algorithm Description

Algorithm name: AdaptMut+Restart+DynMut

The algorithm extends the `AdaptMut` submission from prior years:
* *Triggered Hypermutation:* If stagnation is detected (no fitness increase > 1% in the last 5 generations), the number of applied mutations is increased (max range 1-5)
* The initial population is randomly generated
* Infeasible genotypes are not evaluated (detected with `framsLib.isValidCreature(genotype)`), so they don't count towards the `totalevals` anymore. This saves ~300 evaluations on average.
* *Soft restart mechanism:*
	* patience=10 generations
	* new population = \[25% clone best individual and mutate 0-4 times\] + \[75% randomly generated individuals\]
* *Dynamic mutation probabilities:* Before each mutation, alter the mutation probabilities of the simulator's mutation operators. More information about the update method below:
	* A *Mutation Result Cache* stores the fitness increase/decrease caused by each mutation type in a rolling window (decay=0.985)
		* This means a 300 fitness decrease is 'forgotten' after ~20 generations ~= 1.000 evaluations (-300 * 0.985^{987 generations}<0.0001)
	* The mutation probabilities are recomputed after each generation.
	* The mutation probabilities are the same for all individuals in a generation (i.e. no per-individual mutation probabilities).
	* Invalid individuals (fitness = -999999) are not counted towards the Mutation Result Cache
	* The mutation operators which cause the smallest fitness decrease have the smallest probabilities.
	* The mutation operators which cause the largest fitness decrease have the largest probabilities.
	* A lower bound is set on all mutation probabilities (only those which are not 0 at the start of the program), so no mutation operator can go extinct.
* popsize = 50, pmut=0.8, pxov=0.2
* genformat = 0 (it gives the best result), but it can be used with any genformat
