#ifndef RLS_OBSERVER_APP_H
#define RLS_OBSERVER_APP_H

#include <ti/datapath/dpc/objectdetection/objdethwa/objectdetection.h>

int rls_awr2944p_observer_app_init(void);

void rls_awr2944p_observer_app_process(
    DPC_ObjectDetection_ExecuteResult *result
);

#endif
