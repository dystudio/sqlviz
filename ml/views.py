from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.shortcuts import render_to_response
from django.template import RequestContext
# from django.shortcuts import render
from sklearn import cross_validation, metrics
import statsmodels.formula.api as smf
import statsmodels as sm
import models
import website.query as query
import json
# import logging
# import base64
import pickle
import pandas as pd
from django.conf import settings
import copy


@login_required
def index(request):
    ml_models = models.machine_learning_model.objects.filter()

    return render_to_response(
        'website/ml_index.html',
        {
            'ml_models': ml_models
        },
        context_instance=RequestContext(request))


@login_required
def view_model(request, ml_id):
    pass


@login_required
def build_model(request, ml_id):
    ml = MachineLearning(request, ml_id)
    return ml.build_model()


@login_required
def use_model(request, ml_id):
    ml = MachineLearning(request, ml_id)
    x = pd.DataFrame(json.loads(request.GET.get('data', None)))
    #x = sm.api.add_constant(x)
    return ml.use_model(x)


class MachineLearning:
    def __init__(self, request, ml_id):
        self.request = request
        self.ml_id = ml_id
        self.ml_model = models.machine_learning_model.objects.filter(
                id=ml_id).first()
        self.model = None

    def build_model(self):
        # Build model and return results as API
        if self.ml_model.type == 'logistic':
            return_data = self.logistic_regression()
        elif self.ml_model.type == 'linear':
            return_data = self.linear_regression()
        # save results if requested
        if True:
            self.model_to_db()
        # Return to API
        return return_data

    def use_model(self, x):
        # Find latest model
        self.db_to_model()
        return HttpResponse(json.dumps(self.apply_model(x)),
                            content_type="application/json")

    def prepare_data(self):
        ml_data = self.ml_model
        query_id = ml_data.query_id
        lq = query.LoadQuery(
            query_id=query_id,
            user=self.request.user,
            parameters=self.request.GET.dict(),
            cacheable=self.request.GET.get('cacheable', None)
        )
        q = lq.prepare_query()
        q.run_query()
        q.run_manipulations()
        self.data = q.return_data()
        return self.data

    def build_model_string(self):
        ml_string = []
        print self.data.columns
        print self.data.dtypes
        print self.data.head()
        self.data = self.data.convert_objects(convert_numeric=True)
        print self.data.describe()
        for col_name, col_type in (zip(self.data.columns, self.data.dtypes)):
            if col_name != self.ml_model.target_column:
                if col_type == 'object':
                    ml_string.append('C(%s)' % col_name)
                else:
                    ml_string.append(col_name)
        ml_string = ' + '.join(ml_string)
        ml_string = '%s ~ %s' % (self.ml_model.target_column, ml_string)
        return ml_string.encode("ascii")

    def linear_regression(self):
        self.prepare_data()
        ml_string = self.build_model_string()
        print ml_string
        self.model = smf.ols(formula=ml_string, data=self.data).fit()
        print self.model
        # params = self.model.params.tolist()  # .tolist()
        summary = str(self.model.summary())
        return_data = {
            "data":
                {
                    # "params": params,
                    "summary": summary
                },
            "error": False}
        # print "predicted", self.model.predict(self.data.iloc[0])

        return HttpResponse(json.dumps(return_data),
                            content_type="application/json")

    def apply_model(self, x):
        return self.model.predict(x)

    def logistic_regression(self, test_size=.3):
        self.data = self.prepare_data()
        col_pred = [self.ml_model.target_column]
        cols = [col for col in self.data.columns if col not in col_pred]
        x = self.data[cols]
        y = self.data[col_pred]

        for col_name, col_type in (zip(x.columns, x.dtypes)):
            if col_name != self.ml_model.target_column:
                if col_type == 'object':
                    dummy_ranks = pd.get_dummies(
                            self.data[col_name], prefix=col_name)
                    x = x.join(dummy_ranks)
                    x = x.drop(col_name, 1)
        x_train, x_cv, y_train, y_cv = cross_validation.train_test_split(
                x, y, test_size=test_size)

        self.model = sm.discrete.discrete_model.Logit(y_train, x_train).fit()
        summary = str(self.model.summary())
        params = self.model.params.tolist()

        # calculate AUC
        preds = self.model.predict(x_cv)
        fpr, tpr, thresholds = metrics.roc_curve(y_cv, preds)
        auc = metrics.auc(fpr, tpr)

        return_data = {
            "data":
                {
                    "summary": summary,
                    "params": params,
                    "auc": auc
                },
            "error": False}
        return HttpResponse(json.dumps(return_data),
                            content_type="application/json")

    def model_to_db(self):

        blob = '%smodels/%s.pickle' % \
            (settings.MEDIA_ROOT, self.ml_model.id)
        print "SAVE TO {}".format(blob)
        model = copy.deepcopy(self.model)
        # model.remove_data()
        model.save(blob) # , remove_data=True)
        try:
            obj = models.model_blob.objects.get(model_id=self.ml_model)
            obj.blob = blob
        except models.model_blob.DoesNotExist:
            obj = models.model_blob(model_id=self.ml_model, blob=blob)
        obj.save()

    def db_to_model(self):
        blob = models.model_blob.objects.filter(
                model_id=self.ml_model).last().blob
        self.model = pickle.load(open(blob, "rb"))
        return self.model
