#include "WarCameraRules.h"

void FWarCameraState::SetPreferences(double Look, double Zoom, bool InvertX, bool InvertY)
{
    LookSensitivity = FMath::IsFinite(Look) ? FMath::Clamp(Look, 0.25, 3.0) : 1.0;
    ZoomSensitivity = FMath::IsFinite(Zoom) ? FMath::Clamp(Zoom, 0.25, 3.0) : 1.0;
    bInvertX = InvertX; bInvertY = InvertY;
}

void FWarCameraState::OrbitPixels(double X, double Y)
{
    if (!FMath::IsFinite(X) || !FMath::IsFinite(Y)) return;
    const double NextYaw = Yaw + X * FMath::RadiansToDegrees(0.005) * LookSensitivity * (bInvertX ? -1.0 : 1.0);
    const double NextPitch = Pitch + Y * FMath::RadiansToDegrees(0.003) * LookSensitivity * (bInvertY ? -1.0 : 1.0);
    if (!FMath::IsFinite(NextYaw) || !FMath::IsFinite(NextPitch)) return;
    Yaw = FRotator::NormalizeAxis(NextYaw);
    const double Limit = FMath::RadiansToDegrees(PI / 2.0 - 0.01);
    Pitch = FMath::Clamp(NextPitch, -Limit, Limit);
}

void FWarCameraState::WheelPixels(double Delta)
{
    if (!FMath::IsFinite(Delta)) return;
    const double Next = Distance + Delta * ZoomSensitivity;
    if (!FMath::IsFinite(Next)) return;
    Distance = FMath::Clamp(Next, bIndoor ? 165.0 : 300.0, bIndoor ? 380.0 : 1400.0);
}

void FWarCameraState::SetIndoor(bool bEnabled)
{
    if (bIndoor == bEnabled) return;
    bIndoor = bEnabled;
    if (bIndoor)
    {
        OutdoorDistance = Distance; OutdoorYaw = Yaw; OutdoorPitch = Pitch;
        Distance = 220.0; Yaw = 0.0; Pitch = -FMath::RadiansToDegrees(0.42);
    }
    else
    {
        Distance = FMath::Clamp(OutdoorDistance, 300.0, 1400.0);
        Yaw = OutdoorYaw; Pitch = OutdoorPitch;
    }
}
