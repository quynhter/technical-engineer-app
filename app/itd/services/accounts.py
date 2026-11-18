"""Role-checked account operations; code/session handling stays out of audit payloads."""
from .permissions import ACCOUNT_POLICIES
from .context import ServiceContext
from .operations import operation as service_operation


def execute(accounts, actor, operation, data):
    if operation not in ACCOUNT_POLICIES:
        raise ValueError('Неизвестная операция с пользователями')
    with service_operation(ServiceContext(database=accounts.path), actor,
                           'account:' + operation, ACCOUNT_POLICIES[operation]):
        return _execute(accounts, actor, operation, data)


def _execute(accounts, actor, operation, data):
    if operation == 'list':
        return accounts.list()
    if operation == 'profile':
        return accounts.save_profile(actor.user_id, data)
    if operation == 'rotate-self':
        return accounts.rotate(actor.user_id, actor.user_id)
    if operation == 'create':
        return accounts.create(data)
    if operation not in ('role', 'delete', 'rotate-user'):
        raise ValueError('Неизвестная операция с пользователями')
    return accounts.manage('rotate' if operation == 'rotate-user' else operation, actor.user_id, data)
