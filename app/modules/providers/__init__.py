"""Providers module: DB-backed connection config for external SMM providers.

Not to be confused with app/providers/ (the plugin engine itself). This
module stores *accounts* (name, url, api key, which driver/plugin to use)
and exposes admin CRUD + a "test connection" action that calls into the
plugin via app.providers.registry.
"""
