#!/usr/bin/env python3
"""
Daily enrichment script for processing 1640+ companies
Designed to run without timeouts by processing in chunks
"""

import requests
import time
import json
import sys
from datetime import datetime
import logging

# Configuration
API_URL = "https://awesometesting.info/api-zoho"
API_KEY = "FL8jC4reI_Bg1fY_9x7YRXpg8sfbwmby7I7iJ_7QBIKpDTtWgp8SOs6NUGhA_qIX"
CHUNK_SIZE = 25  # Optimal for ~1 minute per chunk
CONTACTS_PER_COMPANY = 5
FILTER_TYPE = "managers"
MAX_RETRIES = 3
RETRY_DELAY = 10

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'enrichment_{datetime.now().strftime("%Y%m%d")}.log'),
        logging.StreamHandler()
    ]
)

class DailyEnrichmentProcessor:
    def __init__(self):
        self.session_id = f"daily-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        self.total_companies = 0
        self.total_enriched = 0
        self.total_skipped = 0
        self.total_contacts = 0
        self.start_time = time.time()
        
    def process_chunk(self, offset):
        """Process a single chunk of companies"""
        for attempt in range(MAX_RETRIES):
            try:
                logging.info(f"Processing chunk at offset {offset} (attempt {attempt + 1})")
                
                response = requests.post(
                    f"{API_URL}/enrich_companies_chunked",
                    headers={"X-API-Key": API_KEY},
                    json={
                        "chunk_size": CHUNK_SIZE,
                        "start_offset": offset,
                        "contacts_per_company": CONTACTS_PER_COMPANY,
                        "filter_type": FILTER_TYPE,
                        "session_id": self.session_id
                    },
                    timeout=240  # 4-minute timeout per chunk
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    logging.error(f"HTTP {response.status_code}: {response.text}")
                    
            except requests.exceptions.Timeout:
                logging.warning(f"Timeout on chunk {offset}, attempt {attempt + 1}")
            except Exception as e:
                logging.error(f"Error on chunk {offset}: {e}")
            
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)
        
        return None
    
    def run(self):
        """Run the daily enrichment process"""
        logging.info(f"Starting daily enrichment - Session: {self.session_id}")
        offset = 0
        consecutive_failures = 0
        
        while True:
            # Process chunk
            result = self.process_chunk(offset)
            
            if not result:
                consecutive_failures += 1
                if consecutive_failures >= 3:
                    logging.error("Too many consecutive failures, stopping")
                    break
                offset += CHUNK_SIZE
                continue
            
            consecutive_failures = 0
            
            # Update statistics
            results = result.get('results', {})
            chunk_info = result.get('chunk_info', {})
            
            self.total_companies += results.get('companies_analyzed', 0)
            self.total_enriched += results.get('companies_enriched', 0)
            self.total_skipped += results.get('companies_skipped', 0)
            self.total_contacts += results.get('total_contacts_created', 0)
            
            # Log progress
            logging.info(
                f"Progress: {chunk_info.get('progress_percentage', 0):.1f}% | "
                f"Chunk: {results.get('companies_analyzed', 0)} companies | "
                f"Enriched: {results.get('companies_enriched', 0)} | "
                f"Total so far: {self.total_enriched}/{self.total_companies}"
            )
            
            # Check if more chunks exist
            if not chunk_info.get('has_more', False):
                logging.info("No more companies to process")
                break
            
            # Update offset for next chunk
            offset = chunk_info.get('next_offset', offset + CHUNK_SIZE)
            
            # Small delay between chunks
            time.sleep(1)
        
        self.print_summary()
    
    def print_summary(self):
        """Print final summary"""
        elapsed_time = time.time() - self.start_time
        
        summary = f"""
{'='*60}
DAILY ENRICHMENT COMPLETE
{'='*60}
Session ID: {self.session_id}
Total Companies Processed: {self.total_companies}
Companies Enriched: {self.total_enriched}
Companies Skipped: {self.total_skipped}
Total Contacts Created: {self.total_contacts}
Processing Time: {elapsed_time/60:.2f} minutes
Average Time per Company: {elapsed_time/self.total_companies:.2f} seconds
{'='*60}
        """
        
        logging.info(summary)
        
        # Save summary to file
        with open(f'enrichment_summary_{datetime.now().strftime("%Y%m%d")}.txt', 'w') as f:
            f.write(summary)

def estimate_processing_time(total_companies):
    """Estimate processing time for given number of companies"""
    chunks_needed = (total_companies + CHUNK_SIZE - 1) // CHUNK_SIZE
    estimated_seconds = chunks_needed * 60  # ~60 seconds per chunk
    return estimated_seconds / 60  # Return minutes

if __name__ == "__main__":
    # Check if we should run estimation only
    if len(sys.argv) > 1 and sys.argv[1] == "--estimate":
        companies = int(sys.argv[2]) if len(sys.argv) > 2 else 1640
        minutes = estimate_processing_time(companies)
        print(f"Estimated time for {companies} companies: {minutes:.1f} minutes")
        sys.exit(0)
    
    # Run the processor
    processor = DailyEnrichmentProcessor()
    
    try:
        processor.run()
    except KeyboardInterrupt:
        logging.info("Process interrupted by user")
        processor.print_summary()
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        processor.print_summary()
        raise