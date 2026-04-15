Chunk URL design decisions
- Global Queue vs. Async Generator pattern
- Queue Pros
	- Rate Limiting
	- Fan-in data
	- Thread bridging
- Generator
	- More elegant and python-native pattern
	- No global queue
- Decision:
	- Use Async Generator
	- Streaming model operates more immediately and has less latency and stack overhead than a queue and thread pattern
	- Don't need to buffer data at the transfer layer. 
	- Rate limits follows a better design when it's done at the function configuration level rather during transfer stage.
	
	
ETL Pipeline design 
- Hybrid arch
	- Async coroutine based chunker and embedder
		- Fast and non-blocking API calls
		- Minimal throughput bottlenecks
		- Low latency
	- Threaded Milvus inserter 
		- Maintains state
		- Fans out to multiple threads
		- Natively handles backpressure
		- Batching supported
