import datetime
from typing import List

from django.db import models
from django.urls import reverse_lazy
from django.utils.safestring import mark_safe
from model_utils.models import TimeStampedModel

from .defines import MaterialType


class CookbookTag(TimeStampedModel):
    name = models.CharField("菜谱标签", max_length=255)
    priority = models.SmallIntegerField("优先级", default=0)

    cookbook_sum = models.IntegerField("菜谱数量", default=0)

    class Meta:
        verbose_name = "菜谱标签"
        verbose_name_plural = verbose_name

    def __str__(self):
        return f'{self.name}'

    def __repr__(self):
        return f'<CookbookTag>{str(self)}'

    def update_cookbook_sum(self):
        self.cookbook_sum = self.cookbook_set.count()
        self.save()


class Material(TimeStampedModel):
    name = models.CharField("原料名称", max_length=255)
    detail = models.TextField("原料详情", default='')
    type = models.SmallIntegerField("原料类型", choices=(
        (MaterialType.FOOD.value, '食材'),
        (MaterialType.CONDIMENT.value, '调料'),
        (MaterialType.TOOL.value, '工具'),
    ))

    img_url = models.URLField("原料图片", default='')

    step = models.ManyToManyField(
        "Step",
        through='MaterialStepRelationship',
        related_name="material_set"
    )

    class Meta:
        verbose_name = "菜谱原料"
        verbose_name_plural = verbose_name

    def __str__(self):
        return f'{self.name}'


class Step(TimeStampedModel):
    name = models.CharField("步骤名称", max_length=255)
    detail = models.TextField("步骤详情", default='')
    priority = models.SmallIntegerField("优先级", default=0)

    img_url = models.URLField("步骤图片", default='')
    duration = models.DurationField("步骤持续时间", default=datetime.timedelta(minutes=0))

    cookbook = models.ForeignKey(
        "Cookbook",
        on_delete=models.CASCADE,
        related_name="step_set"
    )

    class Meta:
        verbose_name = "菜谱步骤"
        verbose_name_plural = verbose_name

    def __str__(self):
        return f'<步骤>{self.name}'

    def __repr__(self):
        return f'<CookbookStep>{str(self)}'

    def admin_change_page_link(self):
        """
        材料inline中展示的 材料修改页链接
        https://stackoverflow.com/questions/14308050/django-admin-nested-inline
        :return:
        """
        if self.id:
            change_page_url = reverse_lazy(
                'admin:Cookbook_step_change', args=(self.id,)
            )
            return mark_safe(f'<a href="{change_page_url}" target="_blank">修改</a>')
        return '保存后才能修改'
    admin_change_page_link.short_description = '修改按钮'

    @property
    def duration_describe(self) -> str:
        return str(self.duration)

    def get_material_set(self) -> List[Material]:
        return self.material_set.order_by("materialsteprelationship__priority", "id").all()

    def get_material_set_by_type(self, material_type_value: int) -> List[Material]:
        return list(filter(
            lambda material: material.type == material_type_value,
            self.get_material_set()
        ))

    def admin_material_set_list(self):
        materials = self.get_material_set()
        if len(materials) > 0:
            return mark_safe('<br>'.join([
                str(x) for x in self.get_material_set()
            ]))
        return ''
    admin_material_set_list.short_description = '材料'

    @property
    def materials_food(self):
        return self.get_material_set_by_type(MaterialType.FOOD.value)

    @property
    def materials_tool(self):
        return self.get_material_set_by_type(MaterialType.TOOL.value)

    @property
    def materials_condiment(self):
        return self.get_material_set_by_type(MaterialType.CONDIMENT.value)

    def admin_cookbook_url(self):
        if self.id:
            change_page_url = reverse_lazy(
                'admin:Cookbook_cookbook_change', args=(self.cookbook_id,)
            )
            return mark_safe(f'<a href="{change_page_url}">对应菜谱</a>')
        return ''
    admin_cookbook_url.short_description = '对应菜谱'


class Cookbook(TimeStampedModel):
    name = models.CharField("菜谱名称", max_length=255)
    url_video = models.URLField("菜谱视频", default='', blank=True)
    url_cover_image = models.URLField("封面图", default='', blank=True)
    description = models.TextField("描述", default='', blank=True)
    checked = models.BooleanField("检查过 可展示", default=False)

    tag_set = models.ManyToManyField(
        "CookbookTag",
        related_name="cookbook_set",
        blank=True,
        through='TagCookbookRelationship'
    )

    class CookbookPublicManager(models.Manager):
        def get_queryset(self):
            return super().get_queryset().filter(checked=True)

    objects = models.Manager()
    public = CookbookPublicManager()  # 已检查通过 可公开展示的菜谱

    @property
    def materials(self) -> List[Material]:
        return Material.objects.filter(step__cookbook=self).all()

    def add_tag(self, tag: CookbookTag):
        if TagCookbookRelationship.objects.filter(cookbook=self, tag=tag).exists():
            return
        TagCookbookRelationship.objects.create(
            tag=tag, cookbook=self
        )

    class Meta:
        verbose_name = "菜谱"
        verbose_name_plural = verbose_name

    def __str__(self):
        return f'{self.name}'

    def __repr__(self):
        return f'<Cookbook>{self.name}'


class TagCookbookRelationship(models.Model):
    cookbook = models.ForeignKey(Cookbook, on_delete=models.CASCADE)
    tag = models.ForeignKey(CookbookTag, on_delete=models.CASCADE)
    like = models.IntegerField('点赞数量', default=0)
    unlike = models.IntegerField('踩数量', default=0)

    def __str__(self):
        return f'{self.cookbook.name} - {self.tag.name}'


class MaterialStepRelationship(models.Model):
    step = models.ForeignKey(Step, on_delete=models.CASCADE)
    material = models.ForeignKey(Material, on_delete=models.CASCADE)
    amount = models.CharField("原料数量", max_length=255, default='')
    priority = models.SmallIntegerField("优先级", default=0)

    def __str__(self):
        return f'{self.step.name} - {self.material.name}'
