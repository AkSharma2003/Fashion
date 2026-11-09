"""Import every models module so SQLAlchemy metadata (Alembic, tests) sees all tables."""
from app.core import alerts, app_settings, audit, idempotency, outbox, sequences  # noqa: F401
from app.modules.auth import models as auth_models  # noqa: F401
from app.modules.catalog import models as catalog_models  # noqa: F401
from app.modules.customers import models as customer_models  # noqa: F401
from app.modules.employees import models as employee_models  # noqa: F401
from app.modules.fall_pico import models as fall_pico_models  # noqa: F401
from app.modules.inventory import models as inventory_models  # noqa: F401
from app.modules.khata import models as khata_models  # noqa: F401
from app.modules.notifications import models as notification_models  # noqa: F401
from app.modules.orders import models as order_models  # noqa: F401
from app.modules.store import models as store_models  # noqa: F401
from app.modules.payments import models as payment_models  # noqa: F401
from app.modules.pos import models as pos_models  # noqa: F401
from app.modules.purchasing import models as purchasing_models  # noqa: F401
from app.modules.tally import models as tally_models  # noqa: F401
from app.modules.assist import models as assist_models  # noqa: F401
