"""
TeleStore Bot — Production-Ready Telegram Store Platform
Main entry point. Registers all routers, middleware, and starts polling/webhook.
"""

import asyncio
import logging
import sys
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.mongo import MongoStorage
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import settings
from database.connection import init_db, close_db
from middlewares.auth import AuthMiddleware
from middlewares.rate_limit import RateLimitMiddleware
from middlewares.anti_spam import AntiSpamMiddleware
from middlewares.logging import LoggingMiddleware
from middlewares.store_context import StoreContextMiddleware

from handlers.start import router as start_router
from handlers.store import router as store_router
from handlers.products import router as products_router
from handlers.cart import router as cart_router
from handlers.orders import router as orders_router
from handlers.payments import router as payments_router
from handlers.coupons import router as coupons_router
from handlers.referrals import router as referrals_router
from handlers.tickets import router as tickets_router
from handlers.reviews import router as reviews_router
from handlers.search import router as search_router

from handlers.admin.panel import router as admin_router
from handlers.admin.broadcast import router as broadcast_router
from handlers.admin.stores import router as admin_stores_router
from handlers.admin.users import router as admin_users_router
from handlers.admin.analytics import router as admin_analytics_router
from handlers.admin.payments import router as admin_payments_router

from handlers.owner.dashboard import router as owner_dashboard_router
from handlers.owner.products import router as owner_products_router
from handlers.owner.orders import router as owner_orders_router
from handlers.owner.settings import router as owner_settings_router
from handlers.owner.analytics import router as owner_analytics_router
from handlers.owner.coupons import router as owner_coupons_router
from handlers.owner.referrals import router as owner_referrals_router
from handlers.owner.tickets import router as owner_tickets_router
from handlers.owner.payments import router as owner_payments_router
from handlers.owner.broadcast import router as owner_broadcast_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("logs/telestore.log"),
    ],
)
logger = logging.getLogger(__name__)


async def on_startup(bot: Bot) -> None:
    await init_db()
    logger.info("✅ Database connected")

    if settings.USE_WEBHOOK:
        await bot.set_webhook(
            url=f"{settings.WEBHOOK_BASE_URL}{settings.WEBHOOK_PATH}",
            secret_token=settings.WEBHOOK_SECRET,
            allowed_updates=["message", "callback_query", "pre_checkout_query", "successful_payment"],
        )
        logger.info(f"✅ Webhook set: {settings.WEBHOOK_BASE_URL}{settings.WEBHOOK_PATH}")
    else:
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("✅ Polling mode active")

    me = await bot.get_me()
    logger.info(f"🤖 Bot started: @{me.username} (ID: {me.id})")


async def on_shutdown(bot: Bot) -> None:
    await close_db()
    logger.info("🛑 Bot shutdown complete")


def build_dp(storage) -> Dispatcher:
    dp = Dispatcher(storage=storage)

    # Global middlewares (order matters)
    dp.update.outer_middleware(LoggingMiddleware())
    dp.update.outer_middleware(AuthMiddleware())
    dp.update.outer_middleware(RateLimitMiddleware())
    dp.update.outer_middleware(AntiSpamMiddleware())
    dp.message.outer_middleware(StoreContextMiddleware())
    dp.callback_query.outer_middleware(StoreContextMiddleware())

    # Customer routers
    dp.include_router(start_router)
    dp.include_router(store_router)
    dp.include_router(products_router)
    dp.include_router(cart_router)
    dp.include_router(orders_router)
    dp.include_router(payments_router)
    dp.include_router(coupons_router)
    dp.include_router(referrals_router)
    dp.include_router(tickets_router)
    dp.include_router(reviews_router)
    dp.include_router(search_router)

    # Owner routers
    dp.include_router(owner_dashboard_router)
    dp.include_router(owner_products_router)
    dp.include_router(owner_orders_router)
    dp.include_router(owner_settings_router)
    dp.include_router(owner_analytics_router)
    dp.include_router(owner_coupons_router)
    dp.include_router(owner_referrals_router)
    dp.include_router(owner_tickets_router)
    dp.include_router(owner_payments_router)
    dp.include_router(owner_broadcast_router)

    # Super-admin routers
    dp.include_router(admin_router)
    dp.include_router(broadcast_router)
    dp.include_router(admin_stores_router)
    dp.include_router(admin_users_router)
    dp.include_router(admin_analytics_router)
    dp.include_router(admin_payments_router)

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    return dp


async def main() -> None:
    Path("logs").mkdir(exist_ok=True)

    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    storage = MongoStorage.from_url(
        url=settings.MONGODB_URI,
        db_name=settings.MONGODB_DB,
        collection_name="fsm_storage",
    )

    dp = build_dp(storage)

    if settings.USE_WEBHOOK:
        app = web.Application()
        SimpleRequestHandler(
            dispatcher=dp,
            bot=bot,
            secret_token=settings.WEBHOOK_SECRET,
        ).register(app, path=settings.WEBHOOK_PATH)
        setup_application(app, dp, bot=bot)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, host=settings.HOST, port=settings.PORT)
        await site.start()
        logger.info(f"🌐 Webhook server running on {settings.HOST}:{settings.PORT}")
        await asyncio.Event().wait()
    else:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Bot stopped by user")
