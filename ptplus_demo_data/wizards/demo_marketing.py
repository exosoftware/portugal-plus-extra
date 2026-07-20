##############################################################################
#
#    Copyright (C) 2026 Exo Software, Lda. (<https://exosoftware.pt>)
#
##############################################################################
import random
from datetime import timedelta

from odoo import _, fields, models
from odoo.fields import Command


class PtplusDemoDataWizard(models.TransientModel):
    _inherit = "ptplus.demo.data.wizard"

    def _demo_get_or_create_mailing_list(self, partner):
        name = _("Clientes e Prospects")
        contact_list = self.env["mailing.list"].search([("name", "=", name)], limit=1)
        if contact_list:
            return contact_list
        contact_list = self.env["mailing.list"].create({"name": name})
        self.env["mailing.contact"].create(
            {
                "name": partner.name,
                "email": partner.email or False,
                "list_ids": [Command.set([contact_list.id])],
            }
        )
        return contact_list

    def _demo_email_from(self, company):
        # email_from's compute falls back to the acting user's email, which
        # may not be configured in a demo environment; a mailing_type='mail'
        # record requires a non-null value (mailing_mailing_email_from
        # check constraint).
        return company.email or "%s <demo@example.com>" % company.name

    def _demo_generate_mailing_traces(
        self, mailing, contacts, open_rate, click_rate, bounce_rate
    ):
        """Fabricate opens/clicks/bounces for a mailing without sending it.

        mailing.trace only requires model+res_id (mail_mail_id/message_id
        are optional) so these can be created directly -- no real mail.mail
        needs to exist.
        """
        now = fields.Datetime.now()
        vals_list = []
        for contact in contacts:
            roll = random.random()
            sent_dt = now - timedelta(hours=random.randint(1, 72))
            vals = {
                "mass_mailing_id": mailing.id,
                "model": "mailing.contact",
                "res_id": contact.id,
                "email": contact.email,
                "sent_datetime": sent_dt,
            }
            if roll < bounce_rate:
                vals["trace_status"] = "bounce"
            elif roll < bounce_rate + open_rate:
                vals["trace_status"] = "open"
                open_dt = sent_dt + timedelta(minutes=random.randint(5, 500))
                vals["open_datetime"] = open_dt
                if roll < bounce_rate + click_rate:
                    vals["links_click_datetime"] = open_dt + timedelta(
                        minutes=random.randint(1, 60)
                    )
            else:
                vals["trace_status"] = "sent"
            vals_list.append(vals)
        self.env["mailing.trace"].create(vals_list)

    def _demo_generate_email_marketing(self, company, partner):
        log = []
        campaign = self._demo_get_or_create_tag(
            "utm.campaign", _("Campanha de Angariação de Clientes")
        )
        contact_list = self._demo_get_or_create_mailing_list(partner)
        mailing = self.env["mailing.mailing"].create(
            {
                "subject": _("Conheça os nossos serviços de engenharia civil"),
                "body_arch": "<p>%s</p>"
                % _("Descubra os nossos serviços de engenharia civil."),
                "email_from": self._demo_email_from(company),
                "mailing_model_id": self.env["ir.model"]._get("mailing.list").id,
                "contact_list_ids": [Command.set([contact_list.id])],
                "campaign_id": campaign.id,
            }
        )
        log.append(_("Campanha de email marketing criada: %s") % mailing.subject)

        # A/B test: 2 variants sharing one utm.campaign, sent to a 50-contact
        # list, with fabricated engagement stats so the variants compare
        # differently (mailing.mailing.campaign_id + ab_testing_enabled is
        # what pairs them as an A/B test -- see mass_mailing/models/mailing.py).
        ab_list_name = _("Lista de Teste A/B")
        ab_list = self.env["mailing.list"].search(
            [("name", "=", ab_list_name)], limit=1
        )
        if not ab_list:
            ab_list = self.env["mailing.list"].create({"name": ab_list_name})
            self.env["mailing.contact"].create(
                [
                    {
                        "name": _("Contacto Demo %s") % i,
                        "email": "contacto.demo.%s@example.com" % i,
                        "list_ids": [Command.set([ab_list.id])],
                    }
                    for i in range(1, 51)
                ]
            )
        contacts = self.env["mailing.contact"].search([("list_ids", "in", ab_list.id)])

        ab_campaign = self.env["utm.campaign"].create(
            {"name": _("Teste A/B - Lançamento de Serviço")}
        )
        variant_a = self.env["mailing.mailing"].create(
            {
                "subject": _("Descubra os nossos serviços - Variante A"),
                "body_arch": "<p>%s</p>"
                % _("Mensagem direta e objetiva sobre os nossos serviços."),
                "email_from": self._demo_email_from(company),
                "mailing_model_id": self.env["ir.model"]._get("mailing.list").id,
                "contact_list_ids": [Command.set([ab_list.id])],
                "campaign_id": ab_campaign.id,
                "ab_testing_enabled": True,
                "ab_testing_pc": 50,
            }
        )
        variant_b = self.env["mailing.mailing"].create(
            {
                "subject": _("Não perca esta oportunidade - Variante B"),
                "body_arch": "<p>%s</p>"
                % _("Mensagem com apelo à urgência e destaque de benefícios."),
                "email_from": self._demo_email_from(company),
                "mailing_model_id": self.env["ir.model"]._get("mailing.list").id,
                "contact_list_ids": [Command.set([ab_list.id])],
                "campaign_id": ab_campaign.id,
                "ab_testing_enabled": True,
                "ab_testing_pc": 50,
            }
        )
        # Variant A clearly outperforms B, so comparing them is meaningful.
        self._demo_generate_mailing_traces(
            variant_a, contacts, open_rate=0.55, click_rate=0.30, bounce_rate=0.03
        )
        self._demo_generate_mailing_traces(
            variant_b, contacts, open_rate=0.30, click_rate=0.10, bounce_rate=0.08
        )
        ab_campaign.ab_testing_winner_mailing_id = variant_a
        log.append(
            _("Teste A/B criado: '%s' vs '%s' (%s contactos)")
            % (variant_a.subject, variant_b.subject, len(contacts))
        )
        return log

    def _demo_generate_sms(self, company, partner):
        log = []
        contact_list = self._demo_get_or_create_mailing_list(partner)
        sms_template = self.env["sms.template"].create(
            {
                "name": _("SMS Confirmação de Visita Técnica"),
                "model_id": self.env["ir.model"]._get("res.partner").id,
                "body": _("Confirmamos a visita técnica agendada. Equipa %s")
                % company.name,
            }
        )
        sms_mailing = self.env["mailing.mailing"].create(
            {
                "subject": _("Confirmação de Visita Técnica"),
                "mailing_type": "sms",
                "sms_template_id": sms_template.id,
                "body_plaintext": sms_template.body,
                "mailing_model_id": self.env["ir.model"]._get("mailing.list").id,
                "contact_list_ids": [Command.set([contact_list.id])],
            }
        )
        log.append(_("Mailing SMS criado: %s") % sms_mailing.subject)
        return log

    def _demo_generate_whatsapp(self, company, partner):
        log = []
        template = self.env["whatsapp.template"].create(
            {
                "name": _("Confirmação de Orçamento"),
                "body": _(
                    "Olá, o seu orçamento foi enviado. Obrigado por escolher a %s."
                )
                % company.name,
                "model_id": self.env["ir.model"]._get("res.partner").id,
                "lang_code": "pt_PT",
                "template_type": "marketing",
                "status": "approved",
            }
        )
        channel = self.env["discuss.channel"].create(
            {
                "name": _("WhatsApp - %s") % partner.name,
                "channel_type": "whatsapp",
                "whatsapp_number": partner.phone or "+351210000000",
                "whatsapp_partner_id": partner.id,
            }
        )
        channel.message_post(
            body=_("Olá! Obrigado pelo contacto, em breve enviaremos o orçamento.")
        )
        log.append(_("Modelo WhatsApp '%s' e conversa demo criados") % template.name)
        return log

    def _demo_generate_marketing_automation(self, company, partner):
        log = []
        campaign = self.env["marketing.campaign"].create(
            {
                "name": _("Fidelização de Clientes"),
                "model_id": self.env["ir.model"]._get("res.partner").id,
            }
        )
        root_mailing = self.env["mailing.mailing"].create(
            {
                "subject": _("Bem-vindo!"),
                "body_arch": "<p>%s</p>" % _("Obrigado por se juntar a nós."),
                "email_from": self._demo_email_from(company),
                "mailing_model_id": self.env["ir.model"]._get("res.partner").id,
            }
        )
        root_activity = self.env["marketing.activity"].create(
            {
                "name": _("Email de Boas-vindas"),
                "campaign_id": campaign.id,
                "activity_type": "email",
                "trigger_type": "begin",
                "interval_number": 0,
                "interval_type": "hours",
                "mass_mailing_id": root_mailing.id,
            }
        )
        # 4 branches off the root, each triggered by a different engagement
        # outcome (mail_open/mail_not_open/mail_click/mail_bounce) -- valid
        # since their parent (root_activity) is activity_type='email'.
        branches = [
            (_("Follow-up - Abriu o Email"), "mail_open"),
            (_("Follow-up - Não Abriu"), "mail_not_open"),
            (_("Follow-up - Clicou"), "mail_click"),
            (_("Follow-up - Rejeitado"), "mail_bounce"),
        ]
        child_activities = self.env["marketing.activity"]
        for name, trigger_type in branches:
            child_activities |= self.env["marketing.activity"].create(
                {
                    "name": name,
                    "campaign_id": campaign.id,
                    "activity_type": "email",
                    "trigger_type": trigger_type,
                    "parent_id": root_activity.id,
                    "interval_number": 1,
                    "interval_type": "days",
                }
            )

        # Execution data: a participant (creating it auto-seeds a
        # marketing.trace for the root 'begin' activity) plus one
        # "already processed" trace per branch, so each branch shows what
        # was already sent.
        participant = self.env["marketing.participant"].create(
            {"campaign_id": campaign.id, "res_id": partner.id}
        )
        root_trace = self.env["marketing.trace"].search(
            [
                ("participant_id", "=", participant.id),
                ("activity_id", "=", root_activity.id),
            ],
            limit=1,
        )
        now = fields.Datetime.now()
        for child in child_activities:
            self.env["marketing.trace"].create(
                {
                    "participant_id": participant.id,
                    "activity_id": child.id,
                    "parent_id": root_trace.id if root_trace else False,
                    "state": "processed",
                    "schedule_date": now - timedelta(days=random.randint(1, 5)),
                }
            )
        log.append(
            _("Fluxo de marketing automation criado: %s (%s ramos)")
            % (campaign.name, len(child_activities))
        )
        return log

    def _demo_generate_helpdesk(self, company, partner):
        log = []
        # The team name must be unique per company: helpdesk.team auto-creates
        # a mail.alias from it, and mail.alias names are unique database-wide,
        # so re-running this for a second company with the same generic name
        # ("Suporte Técnico") collides with the first company's alias.
        team_name = _("Suporte Técnico - %s") % company.name
        team = self.env["helpdesk.team"].search(
            [("name", "=", team_name), ("company_id", "=", company.id)],
            limit=1,
        )
        if not team:
            team = self.env["helpdesk.team"].create(
                {
                    "name": team_name,
                    "company_id": company.id,
                    "member_ids": [Command.link(self.env.uid)],
                }
            )
        tickets = [
            (_("Pedido de esclarecimento sobre orçamento"), "0"),
            (_("Pedido de fatura duplicada"), "0"),
        ]
        if self._demo_is_civil_engineering():
            tickets += [
                (_("Fissura na parede - necessita vistoria"), "2"),
                (_("Atraso na entrega de materiais"), "1"),
            ]
        for name, priority in tickets:
            self.env["helpdesk.ticket"].create(
                {
                    "name": name,
                    "team_id": team.id,
                    "partner_id": partner.id,
                    "priority": priority,
                }
            )
        log.append(_("%s ticket(s) de apoio ao cliente criados") % len(tickets))
        return log
