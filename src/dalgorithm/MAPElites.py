

"""
This method alters the way in which genotypes are represented/mutated. So it's less an algorithm, but rather a toolbox setup.
"""

#    This file is part of DEAP.
#
#    DEAP is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as
#    published by the Free Software Foundation, either version 3 of
#    the License, or (at your option) any later version.
#
#    DEAP is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public
#    License along with DEAP. If not, see <http://www.gnu.org/licenses/>.
import random
import numpy as np
import math
from deap import tools


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
                offspring[i], = toolbox.mutate(offspring[i])
                del offspring[i].fitness.values

    return offspring

import pandas as pd

def random_gridsel(toolbox, result: pd.DataFrame, df: pd.DataFrame, features: list[str], topk=100000, seed=None):
    """
    Select a random elite
    """
    gridloc = result.sample(n=1, random_state=seed).iloc[0]
    # build mask for equality on all keys
    mask = True
    for k in features:
        mask &= (df[k] == gridloc[k])
    matches = df[mask]
    if matches.empty:
        return None
    max_d = matches["_eval0"].max()
    top = matches[matches["_eval0"] == max_d]
    top = top.sample(n=1, random_state=seed).iloc[0] # random elite if ties are detected.
    top = toolbox.individual_from_str([top['geno_genotype_representation']])
    # assert isinstance(top, str)
    return top

def top_gridsel(toolbox, result: pd.DataFrame, df: pd.DataFrame, features: list[str], topk=50, seed=None):
    """
    Select a random elite
    """
    result = result.sort_values(by="max_eval0", ascending=False).reset_index(drop=True)
    gridloc = result[:topk].sample(n=1, random_state=seed, weights=list(range(len(result[:topk])+1, 1, -1))).iloc[0]
    # build mask for equality on all keys
    mask = True
    for k in features:
        mask &= (df[k] == gridloc[k])
    matches = df[mask]
    if matches.empty:
        return None
    max_d = matches["_eval0"].max()
    top = matches[matches["_eval0"] == max_d]
    top = top.sample(n=1, random_state=seed).iloc[0] # random elite if ties are detected.
    top = toolbox.individual_from_str([top['geno_genotype_representation']])
    # assert isinstance(top, str)
    return top

def curiosity_gridsel(toolbox, result: pd.DataFrame, df: pd.DataFrame, features: list[str], topk=50, seed=None):
    """
    Select a random elite
    """
    result = result.sort_values(by="count", ascending=True).reset_index(drop=True)
    gridloc = result[:topk].sample(n=1, random_state=seed, weights=list(range(len(result[:topk])+1, 1, -1))).iloc[0]
    # build mask for equality on all keys
    mask = True
    for k in features:
        mask &= (df[k] == gridloc[k])
    matches = df[mask]
    if matches.empty:
        return None
    max_d = matches["_eval0"].max()
    top = matches[matches["_eval0"] == max_d]
    top = top.sample(n=1, random_state=seed).iloc[0] # random elite if ties are detected.
    top = toolbox.individual_from_str([top['geno_genotype_representation']])
    # assert isinstance(top, str)
    return top

GRIDSEL_FNS = {
    'random': random_gridsel,
    'quality': top_gridsel, # like random gridsel, but only on top-k individuals (not entire archive)
    'curiosity': curiosity_gridsel, # pick out of the least explored grid cells
    'random_meta': lambda *x, **kx: GRIDSEL_FNS[random.choice([k for k in GRIDSEL_FNS.keys() if k != 'random_meta'])](*x, **kx), # Select one of the above methods at random
}

def mapElites(population, toolbox, cxpb, mutpb, ngen,
            features=['geno_numparts', 'geno_numjoints', 'geno_numneurons', 'geno_numconnections'],
            grid_selection_method='random',
            topk=50,
            restart_patience=15, restart_method='none',
            stats=None, halloffame=None, verbose=__debug__):
    if grid_selection_method == 'random_meta':
        print(list(GRIDSEL_FNS.keys()))
    """
    Taken from deap, adapted for adaptMut, and bootstrapped to mapElites
    """
    grid_selection_method = GRIDSEL_FNS[grid_selection_method]
    logbook = tools.Logbook()
    logbook.header = ['gen', 'nevals'] + (stats.fields if stats else [])

    # Evaluate the individuals with an invalid fitness
    invalid_ind = [ind for ind in population if not ind.fitness.valid]
    fitnesses = toolbox.map(toolbox.evaluate, invalid_ind)
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
        df = toolbox.getArchive()
        df["_eval0"] = df["eval_fit"].apply(lambda x: x[0])
        result = (
            df.groupby(features, dropna=False)
            .agg(count=("_eval0", "size"), max_eval0=("_eval0", "max"))
            .reset_index()
            .sort_values(by="max_eval0", ascending=False)
            .reset_index(drop=True)
        )
        print(result)
        # Select the next generation individuals
        offspring = [grid_selection_method(toolbox, result, toolbox.getArchive(), features, topk=topk) for _ in population]
        # Vary the pool of individuals
        offspring = varAnd(offspring, toolbox, cxpb, mutpb, mutationStrength)

        # Evaluate the individuals with an invalid fitness
        invalid_ind = [ind for ind in offspring if not ind.fitness.valid]
        fitnesses = toolbox.map(toolbox.evaluate, invalid_ind)

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
        # TODO: Add toolbox.generationEnd(population) function, and make it update the CMA-ES parameters there.
        # TODO: Somehow assert that this function is only used with FramsticksLibCompetitionWithHistory

        # Append the current generation statistics to the logbook
        record = stats.compile(population) if stats else {}
        logbook.record(gen=gen, nevals=len(invalid_ind), **record)
        if verbose:
            print(logbook.stream)

        if len(maxFits) > 4:
            bestFitPastConsider = maxFits[-5]
            # bestFitPastConsider = sorted(maxFits[-5:], key=lambda x: x[0], reverse=True)[0]
            if maxFit[0] - bestFitPastConsider[0] < 0.01 * bestFitPastConsider[0]:
                mutationStrength *= 1.1
            else:
                mutationStrength *= 0.9
            mutationStrength = float(np.clip(mutationStrength, 1.0, 5.0))
            print("New mutation strength:", mutationStrength)

        if restart_method != 'none' and len(maxFits) >= restart_patience:
            consider_interval = maxFits[-restart_patience:-1]
            bestFitPast = sorted(consider_interval, key=lambda x: x[0], reverse=True)[0]
            bestFitPastAllConsider = sorted(maxFits, key=lambda x: x[0], reverse=True)[0]
            bestFitPastAll = bestFitPastAllConsider if bestFitPastAllConsider > bestFitPastAll else bestFitPastAll
            ind = consider_interval.index(bestFitPast)
            # for mf in consider_interval:
            #     print(f"({mf[0]:10.5f})")
            # print(len(consider_interval))
            print(f"{maxFits[-1][0]} <= {bestFitPast[0]} and {ind} == {restart_patience}")
            # bestFitPast = maxFits[-restart_patience:]
            if maxFits[-1][0] <= bestFitPast[0] and ind == 0:
                print(maxFits[-1][0], '<=', bestFitPast[0], ', doing a restart...')
                # Drop all cells discovered so far.
                df = toolbox.getArchive()
                df.drop(df.index, inplace=True)
                if restart_method == 'soft_perturb_best':
                    print("Restarting soft_perturb_best after", restart_patience, "gens with no improvement.")
                    population = toolbox.attr_random_pop_from_genotype(bestFitPast[1][0], len(population))
                elif restart_method == 'soft_perturb_best_all':
                    print("Restarting soft_perturb_best_all after", restart_patience, "gens with no improvement.")
                    population = toolbox.attr_random_pop_from_genotype(bestFitPastAll[1][0], len(population))
                elif restart_method == 'hard':
                    print("Restarting hard after", restart_patience, "gens with no improvement.")
                    population = toolbox.population(n=len(population))
                else:
                    raise "Unimplemented restart method: " + restart_method
                
                # Evaluate the individuals with an invalid fitness
                invalid_ind = [ind for ind in population if not ind.fitness.valid]
                fitnesses = toolbox.map(toolbox.evaluate, invalid_ind)
                for ind, fit in zip(invalid_ind, fitnesses):
                    print(ind)
                    ind.fitness.values = fit

                if halloffame is not None:
                    halloffame.update(population)

                record = stats.compile(population) if stats else {}
                logbook.record(gen=f"{gen}.restarting", nevals=len(invalid_ind), **record)
                if verbose:
                    print(logbook.stream)
                
                maxFits = []

    return population, logbook