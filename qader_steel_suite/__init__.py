from . import models
from . import wizard


def pre_init_hook(env):
    """يُستدعى قبل تحميل حقول الموديول عند التثبيت النظيف.

    توقيته هو المقصود: أودو ينادي هذا الخطّاف قبل ``registry.load(package)``
    أي قبل أن تنعكس حقول الموديول في قاعدة البيانات، فيُحذف حقل الاستديو
    المكرّر قبل أن يرى أودو عنوانين متطابقين — ولا يظهر التحذير ولا مرة.
    """
    from .models.studio_cleanup import clean_duplicate_studio_labels
    clean_duplicate_studio_labels(env, stage='pre_init')
