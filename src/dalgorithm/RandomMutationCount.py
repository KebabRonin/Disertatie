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

def varAnd(population, toolbox, cxpb, mutpb, maxmutationsperstep):
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
            # while not toolbox.isValid(offspring[i - 1])[0]:
            #     offspring[i - 1], = toolbox.mutate(offspring[i - 1])
            # while not toolbox.isValid(offspring[i])[0]:
            #     offspring[i], = toolbox.mutate(offspring[i])

    for i in range(len(offspring)):
        if random.random() < mutpb:
            nr_mutations = random.randint(1, maxmutationsperstep)
            for _ in range(nr_mutations):
                offspring[i], = toolbox.mutate(offspring[i])
            del offspring[i].fitness.values
            # while not toolbox.isValid(offspring[i])[0]:
            #     offspring[i], = toolbox.mutate(offspring[i])

    return offspring

def randomMutationCount(population, toolbox, cxpb, mutpb, ngen,
            maxmutationsperstep,
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
        offspring = varAnd(offspring, toolbox, cxpb, mutpb, maxmutationsperstep)

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
                    # ratio_clone = 0.9
                    # cloned_geno_pop = toolbox.attr_random_pop_from_genotype(bestFitPast[1][0], int(len(population) * ratio_clone))
                    # population = cloned_geno_pop + toolbox.population(n=len(population) - len(cloned_geno_pop))
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
                    ind.fitness.values = fit

                if halloffame is not None:
                    halloffame.update(population)

                record = stats.compile(population) if stats else {}
                logbook.record(gen=f"{gen}.restarting", nevals=len(invalid_ind), **record)
                if verbose:
                    print(logbook.stream)
                
                maxFits = []

    return population, logbook