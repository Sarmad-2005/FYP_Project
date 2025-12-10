"""
Scheduler Service
APScheduler-based service for automated refresh routines.
"""

import sys
import os
from flask import Flask, jsonify
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import logging
import atexit

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, project_root)

# Import scheduler from same directory
from scheduler import RefreshScheduler
from backend.a2a_router.router import A2ARouter
from backend.database import DatabaseManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Initialize managers
a2a_router = A2ARouter()
db_manager = DatabaseManager()

# Initialize scheduler
refresh_scheduler = RefreshScheduler(a2a_router, db_manager)

# Initialize APScheduler
scheduler = BackgroundScheduler()
scheduler.start()

# Register with A2A router
a2a_router.register_agent(
    agent_id="scheduler-service",
    agent_url="http://localhost:8005",
    metadata={"service": "scheduler", "version": "1.0"}
)


def financial_refresh_job():
    """Scheduled job for financial refresh"""
    try:
        logger.info("Running scheduled financial refresh job...")
        result = refresh_scheduler.trigger_financial_refresh_all()
        logger.info(f"Financial refresh job completed: {result['successful']}/{result['total_projects']} successful")
    except Exception as e:
        logger.error(f"Error in financial refresh job: {e}")


def performance_refresh_job():
    """Scheduled job for performance refresh"""
    try:
        logger.info("Running scheduled performance refresh job...")
        result = refresh_scheduler.trigger_performance_refresh_all()
        logger.info(f"Performance refresh job completed: {result['successful']}/{result['total_projects']} successful")
    except Exception as e:
        logger.error(f"Error in performance refresh job: {e}")


# Schedule jobs - every 12 hours
scheduler.add_job(
    func=financial_refresh_job,
    trigger=IntervalTrigger(hours=12),
    id='financial_refresh',
    name='Financial Refresh Job',
    replace_existing=True
)

scheduler.add_job(
    func=performance_refresh_job,
    trigger=IntervalTrigger(hours=12),
    id='performance_refresh',
    name='Performance Refresh Job',
    replace_existing=True
)

logger.info("Scheduled jobs configured:")
logger.info("  - Financial refresh: Every 12 hours")
logger.info("  - Performance refresh: Every 12 hours")


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    jobs = scheduler.get_jobs()
    return jsonify({
        "status": "healthy",
        "service": "scheduler-service",
        "port": 8005,
        "scheduled_jobs": len(jobs),
        "jobs": [
            {
                "id": job.id,
                "name": job.name,
                "next_run": job.next_run_time.isoformat() if job.next_run_time else None
            }
            for job in jobs
        ]
    }), 200


@app.route('/trigger/financial', methods=['POST'])
def trigger_financial_refresh():
    """Manually trigger financial refresh for all projects."""
    try:
        result = refresh_scheduler.trigger_financial_refresh_all()
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Error triggering financial refresh: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/trigger/performance', methods=['POST'])
def trigger_performance_refresh():
    """Manually trigger performance refresh for all projects."""
    try:
        result = refresh_scheduler.trigger_performance_refresh_all()
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Error triggering performance refresh: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/trigger/all', methods=['POST'])
def trigger_all_refresh():
    """Manually trigger both financial and performance refresh."""
    try:
        financial_result = refresh_scheduler.trigger_financial_refresh_all()
        performance_result = refresh_scheduler.trigger_performance_refresh_all()
        
        return jsonify({
            "financial": financial_result,
            "performance": performance_result
        }), 200
    except Exception as e:
        logger.error(f"Error triggering all refresh: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/jobs', methods=['GET'])
def get_jobs():
    """Get information about scheduled jobs."""
    try:
        jobs = scheduler.get_jobs()
        jobs_info = [
            {
                "id": job.id,
                "name": job.name,
                "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
                "trigger": str(job.trigger)
            }
            for job in jobs
        ]
        return jsonify({
            "jobs": jobs_info,
            "count": len(jobs)
        }), 200
    except Exception as e:
        logger.error(f"Error getting jobs: {e}")
        return jsonify({"error": str(e)}), 500


# Shutdown scheduler on exit
atexit.register(lambda: scheduler.shutdown())


if __name__ == '__main__':
    logger.info("Starting Scheduler Service on port 8005")
    logger.info("Scheduled jobs will run every 12 hours")
    app.run(host='0.0.0.0', port=8005, debug=True)
