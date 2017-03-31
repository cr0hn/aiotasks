async def start_aiotasks(app):

    if app['aiotasks_run_stand_alone']:
        app['aiotasks'].run()


async def cleanup_aiotasks(app):
    app['aiotasks'].stop()


def setup_aiohttp(app,
                  manager,
                  run_stand_alone: bool = True):
    app['aiotasks'] = manager
    app['aiotasks_run_stand_alone'] = run_stand_alone

    app.on_startup.append(start_aiotasks)
    app.on_cleanup.append(cleanup_aiotasks)
