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

def varAnd(population, toolbox, cxpb, mutpb, mutstrength, xmut_enabled, added_ind):
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
                    ## AdaptMut randomly adds a RANDOM specimen rarely
                    if added_ind == 'initial':
                        offspring[i] = toolbox.individual()
                    elif added_ind == 'random':
                        offspring[i] = toolbox.random_individual()
                else:
                    offspring[i], = toolbox.mutate(offspring[i])
                    del offspring[i].fitness.values

    return offspring

def adaptMut(population, toolbox, cxpb, mutpb, ngen, xmut_enabled, added_ind,
            restart_patience=15, restart_method='none',
            stats=None, halloffame=None, verbose=__debug__):
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
        # Compute crowding distance for the current population.
        toolbox.add_crowding_distance(population)
        # Select the next generation individuals
        offspring = toolbox.select(population, len(population))
        if len(offspring[0].fitness.values) > 1:
            print(f"======== Generation {gen} Chosed:")
            for p in offspring:
                print(f"{float(p.fitness.values[0]):10.5f} {float(p.fitness.values[1]):10.5f} | {str(p)[:40]}")
        # Vary the pool of individuals
        offspring = varAnd(offspring, toolbox, cxpb, mutpb, mutationStrength, xmut_enabled, added_ind=added_ind)

        # Evaluate the individuals with an invalid fitness
        invalid_ind = [ind for ind in offspring if not ind.fitness.valid]
        fitnesses = toolbox.map(toolbox.evaluate, invalid_ind)

        # Only takes into account newly generated individuals. Old folks who persisted unchanged don't contribute to the history.
        maxFit = (float('-inf'), '')
        for ind, fit in zip(invalid_ind, fitnesses):
            ind.fitness.values = fit
            if fit[0] > maxFit[0]:
                maxFit = (fit[0], toolbox.clone(ind))
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
            bestFitPast = maxFits[-5]
            # bestFitPast = sorted(maxFits[-5:], key=lambda x: x[0], reverse=True)[0]
            if maxFit[0] - bestFitPast[0] < 0.01 * bestFitPast[0]:
                mutationStrength *= 1.1
            else:
                mutationStrength *= 0.9
            mutationStrength = float(np.clip(mutationStrength, 1.0, 5.0))
            print("New mutation strength:", mutationStrength)

        if restart_method != 'none' and len(maxFits) >= restart_patience:
            consider_interval = maxFits[-restart_patience:-1]
            bestFitPast = sorted(consider_interval, key=lambda x: x[0], reverse=True)[0]
            ind = consider_interval.index(bestFitPast)
            # for mf in consider_interval:
            #     print(f"({mf[0]:10.5f})")
            # print(len(consider_interval))
            print(f"{maxFits[-1][0]} <= {bestFitPast[0]} and {ind} == {restart_patience}")
            # bestFitPast = maxFits[-restart_patience:]
            if maxFits[-1][0] <= bestFitPast[0] and ind == 0:
                print(maxFits[-1][0], '<=', bestFitPast[0], ', doing a restart...')
                if restart_method == 'soft_perturb_best':
                    print("Restarting soft_perturb_best after", restart_patience, "gens with no improvement.")
                    population = toolbox.attr_random_pop_from_genotype(bestFitPast[1][0], len(population))
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