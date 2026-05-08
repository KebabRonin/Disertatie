import random
from deap import tools
import math, numpy as np

EPS = 1e-20
def s_int(x):
    """Stochastic rounding"""
    a = math.floor(x)
    b = a + 1
    return (np.random.choice([a, b], p=[b - x, x - a]))

def annealer(population, toolbox, ngen, adaptMut=True, temp_schedule='constant', #'exponential',
            adaptMutPatience=15, temperature = 100, cooling_rate=0.9997,
            stats=None, halloffame=None, verbose=__debug__):
    logbook = tools.Logbook()
    logbook.header = ['gen', 'nevals'] + (stats.fields if stats else [])

    assert len(population) == 1

    # Evaluate the individuals with an invalid fitness
    invalid_ind = [ind for ind in population if not ind.fitness.valid]
    fitnesses = toolbox.map(toolbox.evaluate, invalid_ind)
    for ind, fit in zip(invalid_ind, fitnesses):
        ind.fitness.values = fit

    if halloffame is not None:
        halloffame.update(population)

    record = stats.compile(population) if stats is not None else {}
    logbook.record(gen=0, nevals=len(invalid_ind), **record)
    if verbose:
        print(logbook.stream)

    mutationStrength = 1.0
    hist = [population[0].fitness.values]
    # Begin the generational process
    for gen in range(1, ngen + 1):
        # The population only has one individual, so just mutate it lambda times.

        actualMutations = s_int(mutationStrength)
        for _ in range(actualMutations):
            # toolbox.mutate()[0] because it returns a tuple with one element, so we need to unwrap the deap.Individual
            offspring, = toolbox.mutate(toolbox.clone(population[0]))
        del offspring.fitness.values
        # Evaluate the individuals with an invalid fitness
        try:
            offspring.fitness.values = toolbox.evaluate(offspring)
        except ValueError as e:
            print("Error evaluating individual, invalid genotype. Retrying ")

        record = stats.compile([offspring]) if stats is not None else {}
        logbook.record(gen=f"{gen}.mutate", nevals=len(invalid_ind), **record)

        # Update the hall of fame with the generated individuals
        if halloffame is not None:
            halloffame.update([offspring])

        new_cost = offspring.fitness.values[0]
        cost = population[0].fitness.values[0]

        # Boltzman distribution probability
        print("Bolzman threshold: ", math.exp((new_cost - cost) / (temperature + EPS)))
        #Maybe based on the distance from the initial genotype to this one?
        accept_new = new_cost > cost or math.exp((new_cost - cost) / (temperature + EPS)) > random.random()

        if accept_new:
            if not new_cost > cost:
                print('wooo')
            population[0] = offspring

        hist.append(population[0].fitness.values)

        if adaptMut:
            if len(hist) > adaptMutPatience:
                bestFitPast = hist[-adaptMutPatience]
                if hist[0] - bestFitPast[0] < 0.01 * bestFitPast[0]:
                    mutationStrength *= 1.1
                else:
                    mutationStrength *= 0.9
                mutationStrength = float(np.clip(mutationStrength, 1.0, 5.0))
                print("New mutation strength:", mutationStrength)

        # Update temp
        if temp_schedule == 'exponential':
            temperature = np.clip(temperature * cooling_rate, 5, 40)
        elif temp_schedule == 'constant':
            pass
        else:
            raise "Unimplemented temp_schedule: " + temp_schedule

        # Update the statistics with the new population
        record = stats.compile(population) if stats is not None else {}
        logbook.record(gen=gen, nevals=len(invalid_ind), **record)
        if verbose:
            print(logbook.stream)

    return population, logbook