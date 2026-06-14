"""
Test suite for agent isolation by authenticated user.
Verifies that users can only access their own agents.
"""

import pytest
from app import app
from database import SessionLocal
from models import Agent
from auth import get_current_user


@pytest.fixture
def client():
    """Flask test client"""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def db_session():
    """Database session for cleanup"""
    session = SessionLocal()
    yield session
    # Cleanup
    session.query(Agent).delete()
    session.commit()
    session.close()


def create_user_session(client, email):
    """Helper to create a user session"""
    with client.session_transaction() as sess:
        sess['user'] = {
            'user_id': f'auth0|{email}',
            'email': email,
            'name': email.split('@')[0]
        }


class TestAgentCreation:
    """Test that agents are created with authenticated user's email"""

    def test_create_agent_with_auth(self, client):
        """User A creates an agent"""
        create_user_session(client, 'user_a@example.com')

        response = client.post('/agents', json={
            'agent_code': 'print("test")',
            'execution_frequency': 60
        })

        assert response.status_code == 201
        data = response.get_json()
        assert 'agent_id' in data
        assert data['status'] == 'active'

    def test_create_agent_without_auth(self, client):
        """Unauthenticated user cannot create agent"""
        response = client.post('/agents', json={
            'agent_code': 'print("test")',
            'execution_frequency': 60
        })

        assert response.status_code == 401
        assert response.get_json()['error'] == 'Unauthorized'

    def test_agent_user_id_from_session(self, client, db_session):
        """Agent's user_id comes from session, not request body"""
        create_user_session(client, 'user_a@example.com')

        response = client.post('/agents', json={
            'agent_code': 'print("test")',
            'execution_frequency': 60
        })

        agent_id = response.get_json()['agent_id']

        # Check database
        agent = db_session.query(Agent).filter(Agent.agent_id == agent_id).first()
        assert agent is not None
        assert agent.user_id == 'user_a@example.com'


class TestAgentIsolation:
    """Test that users can only see/access their own agents"""

    def test_user_a_sees_only_own_agents(self, client, db_session):
        """User A creates 2 agents, sees only theirs"""
        create_user_session(client, 'user_a@example.com')

        # User A creates 2 agents
        response1 = client.post('/agents', json={
            'agent_code': 'code_a1',
            'execution_frequency': 60
        })
        agent_a1_id = response1.get_json()['agent_id']

        response2 = client.post('/agents', json={
            'agent_code': 'code_a2',
            'execution_frequency': 45
        })
        agent_a2_id = response2.get_json()['agent_id']

        # User A lists agents
        response = client.get('/agents')
        agents = response.get_json()

        assert len(agents) == 2
        agent_ids = [a['agent_id'] for a in agents]
        assert agent_a1_id in agent_ids
        assert agent_a2_id in agent_ids

    def test_user_b_cannot_see_user_a_agents(self, client, db_session):
        """User B doesn't see User A's agents"""
        # User A creates agents
        create_user_session(client, 'user_a@example.com')
        response1 = client.post('/agents', json={
            'agent_code': 'code_a',
            'execution_frequency': 60
        })
        agent_a_id = response1.get_json()['agent_id']

        # User B logs in
        create_user_session(client, 'user_b@example.com')

        # User B lists agents - should be empty
        response = client.get('/agents')
        agents = response.get_json()

        assert len(agents) == 0
        agent_ids = [a['agent_id'] for a in agents]
        assert agent_a_id not in agent_ids

    def test_user_b_cannot_access_user_a_agent(self, client):
        """User B gets 403 when trying to access User A's agent"""
        # User A creates agent
        create_user_session(client, 'user_a@example.com')
        response = client.post('/agents', json={
            'agent_code': 'code_a',
            'execution_frequency': 60
        })
        agent_a_id = response.get_json()['agent_id']

        # User B tries to access it
        create_user_session(client, 'user_b@example.com')
        response = client.get(f'/agents/{agent_a_id}')

        assert response.status_code == 403
        assert response.get_json()['error'] == 'Forbidden'

    def test_user_b_cannot_delete_user_a_agent(self, client):
        """User B cannot delete User A's agent (403)"""
        # User A creates agent
        create_user_session(client, 'user_a@example.com')
        response = client.post('/agents', json={
            'agent_code': 'code_a',
            'execution_frequency': 60
        })
        agent_a_id = response.get_json()['agent_id']

        # User B tries to delete it
        create_user_session(client, 'user_b@example.com')
        response = client.delete(f'/agents/{agent_a_id}')

        assert response.status_code == 403
        assert response.get_json()['error'] == 'Forbidden'

    def test_user_b_cannot_pause_user_a_agent(self, client):
        """User B cannot pause User A's agent (403)"""
        # User A creates agent
        create_user_session(client, 'user_a@example.com')
        response = client.post('/agents', json={
            'agent_code': 'code_a',
            'execution_frequency': 60
        })
        agent_a_id = response.get_json()['agent_id']

        # User B tries to pause it
        create_user_session(client, 'user_b@example.com')
        response = client.patch(f'/agents/{agent_a_id}', json={'status': 'paused'})

        assert response.status_code == 403
        assert response.get_json()['error'] == 'Forbidden'


class TestMultiUserScenario:
    """Test realistic multi-user scenarios"""

    def test_user_a_and_b_both_deploy_agents(self, client):
        """User A and User B each deploy their own agents"""
        # User A deploys agent
        create_user_session(client, 'user_a@example.com')
        response_a = client.post('/agents', json={
            'agent_code': 'code_a',
            'execution_frequency': 60
        })
        agent_a_id = response_a.get_json()['agent_id']

        # User B deploys agent
        create_user_session(client, 'user_b@example.com')
        response_b = client.post('/agents', json={
            'agent_code': 'code_b',
            'execution_frequency': 45
        })
        agent_b_id = response_b.get_json()['agent_id']

        # User A lists agents - should see only A's
        create_user_session(client, 'user_a@example.com')
        response = client.get('/agents')
        agents_a = response.get_json()
        assert len(agents_a) == 1
        assert agents_a[0]['agent_id'] == agent_a_id

        # User B lists agents - should see only B's
        create_user_session(client, 'user_b@example.com')
        response = client.get('/agents')
        agents_b = response.get_json()
        assert len(agents_b) == 1
        assert agents_b[0]['agent_id'] == agent_b_id

    def test_user_can_delete_own_agent(self, client):
        """User can delete their own agent"""
        # User A creates agent
        create_user_session(client, 'user_a@example.com')
        response = client.post('/agents', json={
            'agent_code': 'code_a',
            'execution_frequency': 60
        })
        agent_a_id = response.get_json()['agent_id']

        # User A deletes their own agent
        response = client.delete(f'/agents/{agent_a_id}')
        assert response.status_code == 200

        # Verify it's gone
        response = client.get('/agents')
        agents = response.get_json()
        assert len(agents) == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
