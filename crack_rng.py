
class JavaRandom:
    def __init__(self, seed):
        self.seed = (seed ^ 0x5DEECE66D) & ((1 << 48) - 1)

    def next(self, bits):
        self.seed = (self.seed * 0x5DEECE66D + 0xB) & ((1 << 48) - 1)
        return self.seed >> (48 - bits)

    def nextIntPowerOf2(self, bound):
        # Specialized for bound=65536 (2^16)
        # Returns (bound * next(31)) >> 31
        # effectively next(31) >> 15
        r = self.next(31)
        return (bound * r) >> 31

def simulate_match(seed, num_groups=2):
    rng = JavaRandom(seed)
    
    # Step 1: Randomize groups (nextInt(2))
    r1 = rng.nextIntPowerOf2(2) # Technically nextInt(2) calls normal logic, but 2 is power of 2
    
    # Step 2: Load Warrior 1
    # nextInt(65536)
    pos1 = rng.nextIntPowerOf2(65536)
    
    # Step 3: Randomize groups remaining (nextInt(1)) -> always 0, advances RNG
    rng.nextIntPowerOf2(1) # 1 is power of 2 (2^0)
    
    # Step 4: Load Warrior 2
    pos2 = rng.nextIntPowerOf2(65536)
    
    return pos1, pos2

def brute_force_crack(target_pos1, target_pos2):
    # We observe pos1. 
    # pos1 comes from next(31) >> 15.
    # This corresponds to bits 47..17 of the seed, shifted down by 15?
    # next(31) = seed >> 17.
    # result = (seed >> 17) >> 15 = seed >> 32.
    # So pos1 is exactly the top 16 bits of the current seed (bits 47..32).
    
    # We know the state S_at_pos1 has top 16 bits == target_pos1.
    # Let S = (target_pos1 << 32) + low_32_bits.
    # We need to find low_32_bits such that:
    #   S_next = advance(S)  (this was the nextInt(1) call)
    #   S_next2 = advance(S_next) (this is the nextInt(65536) call)
    #   (S_next2 >> 32) == target_pos2
    
    print(f"Cracking for observations: {target_pos1}, {target_pos2}")
    
    # To simulate 8086 constraints, we can't iterate 2^32.
    # But let's see if we can find it fast.
    
    # Inverse LCG constants?
    # S_next2 = A^2 * S + C'
    # We know S_high. We want S_low.
    
    # Check how many hits we get in a small range to estimate density
    hits = 0
    attempts = 1000000
    
    multiplier = 0x5DEECE66D
    addend = 0xB
    mask = (1 << 48) - 1
    
    # Advance twice function
    # S1 = (S * M + A) & mask
    # S2 = (S1 * M + A) & mask
    # We want (S2 >> 32) == target_pos2
    
    # Precompute combined constants for 2 steps
    # S2 = M(MS+A)+A = M^2 S + MA + A
    M2 = (multiplier * multiplier) & mask
    A2 = (multiplier * addend + addend) & mask
    
    base_s = (target_pos1 << 32)
    
    import time
    start = time.time()
    
    # Brute force a chunk
    for low in range(attempts):
        s = base_s | low
        s2 = (s * M2 + A2) & mask
        if (s2 >> 32) == target_pos2:
            print(f"Found candidate state: {hex(s)}")
            hits += 1
            
    end = time.time()
    print(f"Scanned {attempts} candidates in {end-start:.4f}s")
    print(f"Estimated time for 2^32: {(end-start) * (2**32 / attempts) / 3600:.2f} hours")

target_seed = 123456789
p1, p2 = simulate_match(target_seed)
brute_force_crack(p1, p2)

