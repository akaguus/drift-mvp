from datetime import datetime

from flask import Blueprint, jsonify, request, session
from sqlalchemy.exc import SQLAlchemyError

from database import SessionLocal
from models import Agent, ApiKey, Execution
from auth import get_current_user, require_auth, require_api_key
import scheduler as scheduler_module

agents_bp = Blueprint('agents', __name__)


@agents_bp.route('/agents', methods=['GET'])
@require_auth
def list_agents():
    try:
        current_user = get_current_user()
        if not current_user:
            return jsonify({'error': 'Unauthorized'}), 401

        db_session = SessionLocal()
        # Filter agents by authenticated user
        agents = db_session.query(Agent).filter(Agent.user_id == current_user['email']).all()

        agents_list = [
            {
                'agent_id': agent.agent_id,
                'user_id': agent.user_id,
                'status': agent.status,
                'execution_frequency': agent.execution_frequency,
                'last_executed': agent.last_executed.isoformat() if agent.last_executed else None,
                'created_at': agent.created_at.isoformat()
            }
            for agent in agents
        ]
        db_session.close()
        return jsonify(agents_list), 200
    except SQLAlchemyError as e:
        db_session.close()
        return jsonify({'error': f'Database error: {str(e)}'}), 500
    except Exception as e:
        db_session.close()
        return jsonify({'error': f'Unexpected error: {str(e)}'}), 500


@agents_bp.route('/agents', methods=['POST'])
@require_auth
def create_agent():
    current_user = get_current_user()
    if not current_user:
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.get_json()

    if not data:
        return jsonify({'error': 'No JSON body provided'}), 400

    # Only require agent_code and execution_frequency
    required_fields = ['agent_code', 'execution_frequency']
    missing = [f for f in required_fields if f not in data]
    if missing:
        return jsonify({'error': f'Missing required fields: {", ".join(missing)}'}), 400

    try:
        db_session = SessionLocal()
        agent = Agent(
            user_id=current_user['email'],  # Use authenticated user's email
            agent_code=data['agent_code'],
            execution_frequency=data['execution_frequency'],
            status='active'
        )
        db_session.add(agent)
        db_session.commit()

        response = {
            'agent_id': agent.agent_id,
            'status': agent.status,
            'created_at': agent.created_at.isoformat()
        }
        db_session.close()
        return jsonify(response), 201
    except SQLAlchemyError as e:
        db_session.rollback()
        db_session.close()
        return jsonify({'error': f'Database error: {str(e)}'}), 500
    except Exception as e:
        db_session.close()
        return jsonify({'error': f'Unexpected error: {str(e)}'}), 500


@agents_bp.route('/agents/<agent_id>', methods=['GET'])
@require_auth
def get_agent(agent_id):
    current_user = get_current_user()
    if not current_user:
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        db_session = SessionLocal()
        agent = db_session.query(Agent).filter(Agent.agent_id == agent_id).first()

        if not agent:
            db_session.close()
            return jsonify({'error': 'Agent not found'}), 404

        # Verify ownership
        if agent.user_id != current_user['email']:
            db_session.close()
            return jsonify({'error': 'Forbidden'}), 403

        executions = db_session.query(Execution).filter(
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
        db_session.close()
        return jsonify(response), 200
    except SQLAlchemyError as e:
        db_session.close()
        return jsonify({'error': f'Database error: {str(e)}'}), 500
    except Exception as e:
        db_session.close()
        return jsonify({'error': f'Unexpected error: {str(e)}'}), 500


@agents_bp.route('/agents/<agent_id>', methods=['PATCH'])
@require_auth
def update_agent(agent_id):
    current_user = get_current_user()
    if not current_user:
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.get_json()

    if not data:
        return jsonify({'error': 'No JSON body provided'}), 400

    try:
        db_session = SessionLocal()
        agent = db_session.query(Agent).filter(Agent.agent_id == agent_id).first()

        if not agent:
            db_session.close()
            return jsonify({'error': 'Agent not found'}), 404

        # Verify ownership
        if agent.user_id != current_user['email']:
            db_session.close()
            return jsonify({'error': 'Forbidden'}), 403

        if 'status' in data:
            valid_statuses = ['active', 'inactive', 'paused']
            if data['status'] not in valid_statuses:
                db_session.close()
                return jsonify({'error': f'Invalid status. Must be one of: {", ".join(valid_statuses)}'}), 400
            agent.status = data['status']

        if 'execution_frequency' in data:
            agent.execution_frequency = data['execution_frequency']

        db_session.commit()

        response = {
            'agent_id': agent.agent_id,
            'status': agent.status,
            'execution_frequency': agent.execution_frequency,
            'updated_at': agent.updated_at.isoformat()
        }
        db_session.close()
        return jsonify(response), 200
    except SQLAlchemyError as e:
        db_session.rollback()
        db_session.close()
        return jsonify({'error': f'Database error: {str(e)}'}), 500
    except Exception as e:
        db_session.close()
        return jsonify({'error': f'Unexpected error: {str(e)}'}), 500


@agents_bp.route('/agents/<agent_id>', methods=['DELETE'])
@require_auth
def delete_agent(agent_id):
    current_user = get_current_user()
    if not current_user:
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        db_session = SessionLocal()
        agent = db_session.query(Agent).filter(Agent.agent_id == agent_id).first()

        if not agent:
            db_session.close()
            return jsonify({'error': 'Agent not found'}), 404

        # Verify ownership
        if agent.user_id != current_user['email']:
            db_session.close()
            return jsonify({'error': 'Forbidden'}), 403

        db_session.delete(agent)
        db_session.commit()

        db_session.close()
        return jsonify({'message': 'Agent deleted successfully'}), 200
    except SQLAlchemyError as e:
        db_session.rollback()
        db_session.close()
        return jsonify({'error': f'Database error: {str(e)}'}), 500
    except Exception as e:
        db_session.close()
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
@require_api_key
def claude_skill(api_user_id):
    data = request.get_json()

    if not data:
        return jsonify({'success': False, 'error': 'No JSON body provided'}), 400

    action = data.get('action')
    if action != 'deploy_agent':
        return jsonify({'success': False, 'error': f'Unknown action: {action}'}), 400

    required_fields = ['agent_code', 'execution_frequency']
    missing = [f for f in required_fields if f not in data]
    if missing:
        return jsonify({'success': False, 'error': f'Missing required fields: {", ".join(missing)}'}), 400

    if not data.get('agent_code') or not data['agent_code'].strip():
        return jsonify({'success': False, 'error': 'agent_code cannot be empty'}), 400

    try:
        session = SessionLocal()
        agent = Agent(
            user_id=api_user_id,
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


@agents_bp.route('/api/openai-plugin', methods=['POST'])
@require_api_key
def openai_plugin(api_user_id):
    data = request.get_json()

    if not data:
        return jsonify({'success': False, 'error': 'No JSON body provided'}), 400

    action = data.get('action')
    if action != 'deploy_agent':
        return jsonify({'success': False, 'error': f'Unknown action: {action}'}), 400

    required_fields = ['agent_code', 'execution_frequency']
    missing = [f for f in required_fields if f not in data]
    if missing:
        return jsonify({'success': False, 'error': f'Missing required fields: {", ".join(missing)}'}), 400

    if not data.get('agent_code') or not data['agent_code'].strip():
        return jsonify({'success': False, 'error': 'agent_code cannot be empty'}), 400

    try:
        session = SessionLocal()
        agent = Agent(
            user_id=api_user_id,
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
            'message': 'Agent deployed to Drift'
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


@agents_bp.route('/api/keys', methods=['GET'])
@require_auth
def list_api_keys():
    current_user = get_current_user()
    db_session = SessionLocal()
    try:
        keys = db_session.query(ApiKey).filter(ApiKey.user_id == current_user['email']).all()
        return jsonify([
            {
                'api_key': k.api_key,
                'name': k.name,
                'created_at': k.created_at.isoformat() if k.created_at else None,
                'last_used_at': k.last_used_at.isoformat() if k.last_used_at else None,
            }
            for k in keys
        ]), 200
    finally:
        db_session.close()


@agents_bp.route('/api/keys', methods=['POST'])
@require_auth
def create_api_key():
    current_user = get_current_user()
    data = request.get_json(silent=True) or {}

    db_session = SessionLocal()
    try:
        key = ApiKey(user_id=current_user['email'], name=data.get('name'))
        db_session.add(key)
        db_session.commit()

        return jsonify({
            'api_key': key.api_key,
            'name': key.name,
            'created_at': key.created_at.isoformat(),
        }), 201
    except SQLAlchemyError as e:
        db_session.rollback()
        return jsonify({'error': f'Database error: {str(e)}'}), 500
    finally:
        db_session.close()


@agents_bp.route('/api/keys/<key_id>', methods=['DELETE'])
@require_auth
def revoke_api_key(key_id):
    current_user = get_current_user()
    db_session = SessionLocal()
    try:
        key = db_session.query(ApiKey).filter(ApiKey.api_key == key_id).first()
        if not key:
            return jsonify({'error': 'Not found'}), 404
        if key.user_id != current_user['email']:
            return jsonify({'error': 'Forbidden'}), 403

        db_session.delete(key)
        db_session.commit()
        return jsonify({'success': True}), 200
    except SQLAlchemyError as e:
        db_session.rollback()
        return jsonify({'error': f'Database error: {str(e)}'}), 500
    finally:
        db_session.close()
