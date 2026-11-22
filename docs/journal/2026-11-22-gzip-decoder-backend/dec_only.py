import sys, time, rapidgzip, hashlib
p, P, rb = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]) << 20
buf = bytearray(rb); mv = memoryview(buf)
t = time.perf_counter(); c = time.process_time(); n = 0
with rapidgzip.open(p, parallelization=P) as f:
    while k := f.readinto(mv): n += k
print(f"P={P} read={rb>>20}MiB: {n} bytes {time.perf_counter()-t:.1f}s wall {time.process_time()-c:.1f}s cpu")
