"""Small functional workflow, including exactly two competing writes; not a load test."""
import argparse
import concurrent.futures
import json
import os
from pathlib import Path
import threading
import urllib.error
import urllib.request
import uuid


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', default='http://127.0.0.1:8080')
    parser.add_argument('--secondary-url', default=None)
    parser.add_argument('--output', default='artifacts/functional-smoke.json')
    args = parser.parse_args()
    password = os.environ.get('ACADEMIC_ADMIN_PASSWORD')
    if not password:
        parser.error('Set ACADEMIC_ADMIN_PASSWORD for an isolated test/demo environment.')
    second = args.secondary_url or args.url

    def request(base, method, path, body=None, token=None):
        headers = {'Content-Type': 'application/json'}
        if token:
            headers['Authorization'] = 'Bearer ' + token
        data = None if body is None else json.dumps(body, ensure_ascii=False).encode('utf-8')
        req = urllib.request.Request(base.rstrip('/') + path, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=15) as response:
                return response.status, json.load(response)
        except urllib.error.HTTPError as error:
            return error.code, json.load(error)

    def ok(base, method, path, body=None, token=None):
        status, result = request(base, method, path, body, token)
        assert status == 200, (path, status, result.get('code'), result.get('message'))
        return result

    admin = ok(args.url, 'POST', '/api/auth/login', {'username': 'admin', 'password': password})['token']
    assert ok(second, 'GET', '/api/auth/me', token=admin)['role'] == 'ADMIN'
    suffix = uuid.uuid4().hex[:12]
    username = 'smoke-' + suffix
    user_password = uuid.uuid4().hex + 'Aa!'
    account = ok(args.url, 'POST', '/api/auth/register', {'username': username, 'password': user_password, 'displayName': '功能验证临时账号'})
    user = ok(args.url, 'POST', '/api/auth/login', {'username': username, 'password': user_password})['token']

    def action(claim, name, token, base=args.url):
        return ok(base, 'POST', f'/api/claims/{claim["id"]}/actions', {'version': claim['version'], 'action': name, 'reason': '功能验证依据', 'evidence': None}, token)

    identity = ok(args.url, 'POST', '/api/claims', {'kind': 'IDENTITY', 'targetId': account['id'], 'evidence': '隔离环境功能验证身份材料', 'contributionRole': ''}, user)
    identity = action(action(action(identity, 'SUBMIT', user), 'TAKE', admin), 'APPROVE', admin, second)
    assert identity['state'] == 'APPROVED'
    assert ok(args.url, 'GET', '/api/auth/me', token=user)['role'] == 'RESEARCHER'
    scholar_id = 'smoke-' + suffix
    ok(args.url, 'POST', '/api/admin/scholars', {'id': scholar_id, 'name': '功能验证人物', 'institutionId': 'I1', 'bio': '模拟测试人物，不是真实学者。', 'simulated': True}, admin)
    claim = ok(args.url, 'POST', '/api/claims', {'kind': 'PORTAL', 'targetId': scholar_id, 'evidence': '功能验证门户材料', 'contributionRole': ''}, user)
    claim = action(action(claim, 'SUBMIT', user), 'TAKE', admin)
    barrier = threading.Barrier(2)

    def compete(base, name, token):
        barrier.wait(timeout=10)
        status, _ = request(base, 'POST', f'/api/claims/{claim["id"]}/actions', {'version': claim['version'], 'action': name, 'reason': '两请求竞争功能验证', 'evidence': None}, token)
        return status

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        approval = executor.submit(compete, second, 'APPROVE', admin)
        withdrawal = executor.submit(compete, args.url, 'WITHDRAW', user)
        statuses = sorted([approval.result(), withdrawal.result()])
    assert statuses == [200, 409], statuses
    final = ok(args.url, 'GET', '/api/claims/' + claim['id'], token=user)
    profile = ok(second, 'GET', '/api/auth/me', token=user)
    assert (profile['scholarId'] == scholar_id) == (final['state'] == 'APPROVED')
    other = ok(args.url, 'POST', '/api/auth/login', {'username': 'reader', 'password': password})['token']
    assert request(second, 'GET', '/api/claims/' + claim['id'], token=other)[0] == 403
    for token in (admin, user, other):
        ok(args.url, 'POST', '/api/auth/logout', {}, token)
    result = {'ok': True, 'primary': args.url, 'secondary': second,
              'sharedSession': True, 'identityWorkflow': True, 'privateEvidence': True,
              'competingRequests': 2, 'statuses': statuses, 'finalState': final['state'],
              'note': 'Functional checks only; no load test, throughput or p95 result.'}
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
