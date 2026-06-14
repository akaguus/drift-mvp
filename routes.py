from datetime import datetime

from flask import Blueprint, jsonify, request
from sqlalchemy.exc import SQLAlchemyError

from database import SessionLocal
from models import Agent, Execution
import scheduler as scheduler_module

agents_bp = Blueprint('agents', __name__)


@agents_bp.route('/agents', methods=['POST'])
def create_agent():
    data = request.get_json()

    if not data:
        return jsonify({'error': 'No JSON body provided'}), 400

    required_fields = ['user_id', 'agent_code', 'execution_frequency']
    missing = [f for f in required_fields if f not in data]
    if missing:
        return jsonify({'error': f'Missing required fields: {", ".join(missing)}'}), 400

    try:
        session = SessionLocal()
        agent = Agent(
            user_id=data['user_id'],
            agent_code=data['agent_code'],
            execution_frequency=data['execution_frequency'],
            status='active'
        )
        session.add(agent)
        session.commit()

        response = {
            'agent_id': agent.agent_id,
            'status': agent.status,
            'created_at': agent.created_at.isoformat()
        }
        session.close()
        return jsonify(response), 201
    except SQLAlchemyError as e:
        session.rollback()
        session.close()
        return jsonify({'error': f'Database error: {str(e)}'}), 500
    except Exception as e:
        session.close()
        return jsonify({'error': f'Unexpected error: {str(e)}'}), 500


@agents_bp.route('/agents/<agent_id>', methods=['GET'])
def get_agent(agent_id):
    try:
        session = SessionLocal()
        agent = session.query(Agent).filter(Agent.agent_id == agent_id).first()

        if not agent:
            session.close()
            return jsonify({'error': 'Agent not found'}), 404

        executions = session.query(Execution).filter(
            Execution.agent_id == agent_id
        ).order_by(Execution.executed_at.desc()).limit(10).all()

        execution_history = [
            {
                'executed_at': e.executed_at.isoformat(),
                'result': e.result,
                'trade_executed': e.trade_executed
            }
            for e in executions
        ]

        response = {
            'agent_id': agent.agent_id,
            'user_id': agent.user_id,
            'status': agent.status,
            'execution_frequency': agent.execution_frequency,
            'last_executed': agent.last_executed.isoformat() if agent.last_executed else None,
            'execution_history': execution_history
        }
        session.close()
        return jsonify(response), 200
    except SQLAlchemyError as e:
        session.close()
        return jsonify({'error': f'Database error: {str(e)}'}), 500
    except Exception as e:
        session.close()
        return jsonify({'error': f'Unexpected error: {str(e)}'}), 500


@agents_bp.route('/scheduler/status', methods=['GET'])
def scheduler_status():
    scheduler = scheduler_module._scheduler_instance
    if not scheduler:
        return jsonify({'error': 'Scheduler not initialized'}), 500

    return jsonify({
        'running': scheduler.running,
        'last_check': scheduler.last_check.isoformat() if scheduler.last_check else None,
        'agents_executed_today': scheduler.agents_executed_today
    }), 200


@agents_bp.route('/api/claude-skill', methods=['POST'])
def claude_skill():
    data = request.get_json()

    if not data:
        return jsonify({'success': False, 'error': 'No JSON body provided'}), 400

    action = data.get('action')
    if action != 'deploy_agent':
        return jsonify({'success': False, 'error': f'Unknown action: {action}'}), 400

    required_fields = ['user_id', 'agent_code', 'execution_frequency']
    missing = [f for f in required_fields if f not in data]
    if missing:
        return jsonify({'success': False, 'error': f'Missing required fields: {", ".join(missing)}'}), 400

    if not data.get('agent_code') or not data['agent_code'].strip():
        return jsonify({'success': False, 'error': 'agent_code cannot be empty'}), 400

    try:
        session = SessionLocal()
        agent = Agent(
            user_id=data['user_id'],
            agent_code=data['agent_code'],
            execution_frequency=data['execution_frequency'],
            status='active'
        )
        session.add(agent)
        session.commit()

        response = {
            'success': True,
            'agent_id': agent.agent_id,
            'status': agent.status,
            'message': 'Agent deployed successfully'
        }
        session.close()
        return jsonify(response), 201
    except SQLAlchemyError as e:
        session.rollback()
        session.close()
        return jsonify({'success': False, 'error': f'Database error: {str(e)}'}), 500
    except Exception as e:
        session.close()
        return jsonify({'success': False, 'error': f'Unexpected error: {str(e)}'}), 500
