#pragma once
#include "CoreMinimal.h"

/** Browser camera distances are metres; native distances are centimetres. This state is client-local. */
struct AEGISWAR_API FWarCameraState
{
    double Distance = 700.0;
    double Yaw = 0.0;
    double Pitch = -FMath::RadiansToDegrees(0.45);
    double LookSensitivity = 1.0, ZoomSensitivity = 1.0;
    bool bInvertX = false, bInvertY = false;
    void SetPreferences(double Look, double Zoom, bool InvertX, bool InvertY);
    void OrbitPixels(double X, double Y);
    void WheelPixels(double Delta);
    void SetIndoor(bool bEnabled);
    bool IsIndoor() const { return bIndoor; }
private:
    bool bIndoor = false;
    double OutdoorDistance = 700.0, OutdoorYaw = 0.0, OutdoorPitch = -FMath::RadiansToDegrees(0.45);
};
