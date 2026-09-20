"""Server-owned price catalog. Configuration alone never grants access."""
PLANS = {
    'monthly': {'name': 'Mensual', 'amount_cents': 1000, 'currency': 'usd',
                'billing_type': 'manual_renewal', 'interval': 'month', 'permanent': False},
    'one_time': {'name': 'Pago único', 'amount_cents': 4000, 'currency': 'usd',
                 'billing_type': 'one_time', 'interval': None, 'permanent': True},
}


def public_plans():
    # Payment activation remains disabled until provider configuration and tests.
    return {'payments_enabled': False,
            'plans': [dict(id=key, **value) for key, value in PLANS.items()]}
