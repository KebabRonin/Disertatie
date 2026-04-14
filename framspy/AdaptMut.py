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

def varAnd(population, toolbox, cxpb, mutpb, mutstrength, xmut_enabled):
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
                if xmut_enabled and random.random() < 0.01:
                    ## AdaptMut randomly adds a specimen rarely
                    offspring[i] = toolbox.individual()
                else:
                    offspring[i], = toolbox.mutate(offspring[i])
                    del offspring[i].fitness.values

    return offspring

def adaptMut(population, toolbox, cxpb, mutpb, ngen, xmut_enabled, stats=None,
             halloffame=None, verbose=__debug__):
    """
    Taken from deap, adapted for adaptMut
    """
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

    # Begin the generational process
    for gen in range(1, ngen + 1):
        # Select the next generation individuals
        offspring = toolbox.select(population, len(population))

        # Vary the pool of individuals
        offspring = varAnd(offspring, toolbox, cxpb, mutpb, mutationStrength, xmut_enabled)

        # Evaluate the individuals with an invalid fitness
        invalid_ind = [ind for ind in offspring if not ind.fitness.valid]
        fitnesses = toolbox.map(toolbox.evaluate, invalid_ind)
        maxFit = float('-inf')
        for ind, fit in zip(invalid_ind, fitnesses):
            ind.fitness.values = fit
            maxFit = max(maxFit, fit[0])
        maxFits.append(maxFit)

        if len(maxFits) > 4 and np.abs(maxFit - maxFits[-5]) < 0.01 * maxFits[-5]:
            mutationStrength *= 1.1
        else:
            mutationStrength *= 0.9
        mutationStrength = float(np.clip(mutationStrength, 1.0, 5.0))

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

    return population, logbook