/**
 * Concurrency control utilities to prevent overwhelming system resources
 */

export class Semaphore {
  private permits: number;
  private tasks: (() => void)[] = [];

  constructor(permits: number) {
    this.permits = permits;
  }

  async acquire(): Promise<void> {
    if (this.permits > 0) {
      this.permits--;
      return Promise.resolve();
    }

    return new Promise<void>((resolve) => {
      this.tasks.push(resolve);
    });
  }

  release(): void {
    this.permits++;
    const nextTask = this.tasks.shift();
    if (nextTask) {
      this.permits--;
      nextTask();
    }
  }

  async execute<T>(fn: () => Promise<T>): Promise<T> {
    await this.acquire();
    try {
      return await fn();
    } finally {
      this.release();
    }
  }
}

/**
 * Process items in parallel with a concurrency limit
 */
export async function parallelLimit<T, R>(
  items: T[],
  limit: number,
  fn: (item: T, index: number) => Promise<R>
): Promise<R[]> {
  const semaphore = new Semaphore(limit);
  const promises = items.map((item, index) =>
    semaphore.execute(() => fn(item, index))
  );
  return Promise.all(promises);
}

/**
 * Configuration for concurrency limits
 */
export const ConcurrencyConfig = {
  // Max parallel resume processing (full analysis per resume)
  MAX_RESUME_PROCESSING: 2,

  // Max parallel LLM calls across all operations
  MAX_LLM_CALLS: 3,

  // Max parallel PDF parsing
  MAX_PDF_PARSING: 5,

  // Timeout for individual LLM calls (ms)
  LLM_TIMEOUT: 60000,
};

/**
 * Detect if we should use conservative (sequential) processing
 * based on system capabilities
 */
export function shouldUseConservativeMode(): boolean {
  // Check if low memory mode is needed
  if (typeof navigator !== 'undefined') {
    // @ts-ignore - deviceMemory is experimental
    const deviceMemory = navigator.deviceMemory;

    // If device has less than 4GB RAM, use conservative mode
    if (deviceMemory && deviceMemory < 4) {
      return true;
    }

    // @ts-ignore - hardwareConcurrency
    const cores = navigator.hardwareConcurrency;

    // If device has less than 4 cores, use conservative mode
    if (cores && cores < 4) {
      return true;
    }
  }

  return false;
}
