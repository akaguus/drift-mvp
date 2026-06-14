import threading
from datetime import datetime, time

import pytz

from database import SessionLocal
from models import Agent, Execution

_scheduler_instance = None


class Scheduler:
    def __init__(self):
        self.running = False
        self.last_check = None
        self.agents_executed_today = 0
        self.thread = None
        self.eastern = pytz.timezone('US/Eastern')

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False

    def _run(self):
        while self.running:
            try:
                self._check_and_execute()
            except Exception as e:
                print(f"Scheduler error: {e}")

            threading.Event().wait(60)

    def _check_and_execute(self):
        self.last_check = datetime.utcnow()

        session = SessionLocal()
        agents = session.query(Agent).filter(Agent.status == 'active').all()

        for agent in agents:
            self._check_agent(agent, session)

        session.close()

    def _check_agent(self, agent, session):
        now = datetime.utcnow()

        if agent.last_executed is None:
            is_due = True
        else:
            minutes_since = (now - agent.last_executed).total_seconds() / 60
            is_due = minutes_since >= agent.execution_frequency

        if not is_due:
            return

        current_time_et = datetime.now(self.eastern).time()
        market_hours_start = time(9, 30)
        market_hours_end = time(16, 0)

        in_market_hours = market_hours_start <= current_time_et <= market_hours_end

        result = self._execute_agent(agent, in_market_hours)

        execution = Execution(
            agent_id=agent.agent_id,
            executed_at=now,
            result=result['output'],
            trade_executed=result['trade_executed'],
            error_message=result['error']
        )

        session.add(execution)

        agent.last_executed = now
        session.commit()

        if in_market_hours and not result['skipped']:
            self.agents_executed_today += 1

    def _execute_agent(self, agent, in_market_hours):
        market_data = {
            'current_price': 150.25,
            'volume': 1000000,
            'timestamp': datetime.utcnow().isoformat()
        }

        restricted_globals = {'market_data': market_data, '__builtins__': {}}

        if not in_market_hours:
            return {
                'output': 'Skipped: outside market hours',
                'trade_executed': False,
                'error': None,
                'skipped': True
            }

        try:
            exec(agent.agent_code, restricted_globals)

            return {
                'output': 'Execution successful',
                'trade_executed': False,
                'error': None,
                'skipped': False
            }
        except Exception as e:
            return {
                'output': '',
                'trade_executed': False,
                'error': str(e),
                'skipped': False
            }
