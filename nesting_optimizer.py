import random
import time
import numpy as np
from deap import base, creator, tools, algorithms
from shapely.geometry import Point, Polygon
from shapely.affinity import rotate, translate
from geometry_utils import create_part_from_dict, get_part_bounds

class NestingOptimizer:
    def __init__(self, sheet_width=2000, sheet_height=1000, population_size=50, 
                 generations=30, mutation_rate=0.1):
        self.sheet_width = sheet_width
        self.sheet_height = sheet_height
        self.population_size = population_size
        self.generations = generations
        self.mutation_rate = mutation_rate
        
        # Expand parts list to include quantities
        self.parts = []
        self.setup_deap()
    
    def expand_parts_list(self, parts_data):
        """Expand parts list based on quantities"""
        expanded_parts = []
        for part in parts_data:
            quantity = part.get('quantity', 1)
            for i in range(quantity):
                part_copy = part.copy()
                part_copy['id'] = f"{part['id']}_{i+1}" if quantity > 1 else part['id']
                expanded_parts.append(part_copy)
        return expanded_parts
    
    def setup_deap(self):
        """Setup DEAP genetic algorithm components"""
        # Create fitness class (maximize utilization)
        if not hasattr(creator, "FitnessMax"):
            creator.create("FitnessMax", base.Fitness, weights=(1.0,))
        if not hasattr(creator, "Individual"):
            creator.create("Individual", list, fitness=creator.FitnessMax)
        
        self.toolbox = base.Toolbox()
        
        # Register genetic operators
        self.toolbox.register("evaluate", self.evaluate_layout)
        self.toolbox.register("mate", self.crossover)
        self.toolbox.register("mutate", self.mutate)
        self.toolbox.register("select", tools.selTournament, tournsize=3)
    
    def create_individual(self):
        """Create a random individual (layout solution)"""
        individual = []
        for part in self.parts:
            # Random position and rotation for each part
            x = random.uniform(0, self.sheet_width)
            y = random.uniform(0, self.sheet_height)
            rotation = random.uniform(0, 2 * np.pi)
            individual.extend([x, y, rotation])
        return creator.Individual(individual)
    
    def decode_individual(self, individual):
        """Decode individual into list of (part, x, y, rotation)"""
        layout = []
        for i, part in enumerate(self.parts):
            idx = i * 3
            x, y, rotation = individual[idx:idx+3]
            layout.append((part, x, y, rotation))
        return layout
    
    def evaluate_layout(self, individual):
        """Evaluate fitness of a layout"""
        layout = self.decode_individual(individual)
        
        placed_parts = []
        total_area = 0
        
        for part_info, x, y, rotation in layout:
            try:
                # Create geometric shape
                part_shape = create_part_from_dict(part_info)
                
                # Apply rotation and translation
                if rotation != 0:
                    part_shape = rotate(part_shape, rotation, use_radians=True, origin='center')
                part_shape = translate(part_shape, x, y)
                
                # Check if part fits within sheet bounds
                bounds = part_shape.bounds
                if (bounds[0] >= 0 and bounds[1] >= 0 and 
                    bounds[2] <= self.sheet_width and bounds[3] <= self.sheet_height):
                    
                    # Check for overlaps with already placed parts
                    overlaps = False
                    for placed_shape in placed_parts:
                        if part_shape.intersects(placed_shape):
                            overlap_area = part_shape.intersection(placed_shape).area
                            if overlap_area > 1e-6:  # Small tolerance for floating point errors
                                overlaps = True
                                break
                    
                    if not overlaps:
                        placed_parts.append(part_shape)
                        total_area += part_shape.area
            
            except Exception:
                continue  # Skip invalid parts
        
        # Calculate utilization
        sheet_area = self.sheet_width * self.sheet_height
        utilization = (total_area / sheet_area) * 100 if sheet_area > 0 else 0
        
        # Penalize for not placing all parts
        placement_ratio = len(placed_parts) / len(self.parts) if self.parts else 0
        
        # Combined fitness: utilization weighted by placement success
        fitness = utilization * (0.5 + 0.5 * placement_ratio)
        
        return (fitness,)
    
    def crossover(self, ind1, ind2):
        """Crossover operation for two individuals"""
        # Single point crossover
        if len(ind1) > 3:
            # Ensure we cross at part boundaries (multiples of 3)
            cross_point = random.randrange(1, len(ind1) // 3) * 3
            ind1[cross_point:], ind2[cross_point:] = ind2[cross_point:], ind1[cross_point:]
        
        del ind1.fitness.values
        del ind2.fitness.values
        return ind1, ind2
    
    def mutate(self, individual):
        """Mutation operation"""
        for i in range(0, len(individual), 3):
            if random.random() < self.mutation_rate:
                # Mutate position
                if random.random() < 0.5:
                    individual[i] = random.uniform(0, self.sheet_width)     # x
                    individual[i+1] = random.uniform(0, self.sheet_height)  # y
                else:
                    # Mutate rotation
                    individual[i+2] = random.uniform(0, 2 * np.pi)
        
        del individual.fitness.values
        return (individual,)
    
    def optimize(self, parts_data):
        """Run genetic algorithm optimization"""
        start_time = time.time()
        
        # Expand parts based on quantities
        self.parts = self.expand_parts_list(parts_data)
        
        # Register individual creation
        self.toolbox.register("individual", self.create_individual)
        self.toolbox.register("population", tools.initRepeat, list, self.toolbox.individual)
        
        # Create initial population
        population = self.toolbox.population(n=self.population_size)
        
        # Run genetic algorithm
        algorithms.eaSimple(
            population, self.toolbox,
            cxpb=0.7,  # Crossover probability
            mutpb=0.2,  # Mutation probability
            ngen=self.generations,
            verbose=False
        )
        
        # Get best individual
        best_individual = tools.selBest(population, 1)[0]
        best_layout = self.decode_individual(best_individual)
        
        # Calculate final statistics
        stats = self.calculate_layout_stats(best_layout)
        stats['optimization_time'] = time.time() - start_time
        
        return best_layout, stats
    
    def calculate_layout_stats(self, layout):
        """Calculate statistics for a given layout"""
        placed_parts = []
        total_area = 0
        parts_placed = 0
        
        for part_info, x, y, rotation in layout:
            try:
                # Create and transform part
                part_shape = create_part_from_dict(part_info)
                if rotation != 0:
                    part_shape = rotate(part_shape, rotation, use_radians=True, origin='center')
                part_shape = translate(part_shape, x, y)
                
                # Check validity
                bounds = part_shape.bounds
                if (bounds[0] >= 0 and bounds[1] >= 0 and 
                    bounds[2] <= self.sheet_width and bounds[3] <= self.sheet_height):
                    
                    # Check overlaps
                    valid = True
                    for placed_shape in placed_parts:
                        if part_shape.intersects(placed_shape):
                            if part_shape.intersection(placed_shape).area > 1e-6:
                                valid = False
                                break
                    
                    if valid:
                        placed_parts.append(part_shape)
                        total_area += part_shape.area
                        parts_placed += 1
            
            except Exception:
                continue
        
        sheet_area = self.sheet_width * self.sheet_height
        utilization = (total_area / sheet_area) * 100
        waste_area = sheet_area - total_area
        
        return {
            'utilization': utilization,
            'parts_placed': parts_placed,
            'total_parts': len(self.parts),
            'total_area': total_area,
            'sheet_area': sheet_area,
            'waste_area': waste_area
        }
    
    def create_random_layout(self, parts_data):
        """Create a random layout for comparison"""
        self.parts = self.expand_parts_list(parts_data)
        
        layout = []
        for part in self.parts:
            x = random.uniform(0, self.sheet_width)
            y = random.uniform(0, self.sheet_height)
            rotation = random.uniform(0, 2 * np.pi)
            layout.append((part, x, y, rotation))
        
        stats = self.calculate_layout_stats(layout)
        return layout, stats
