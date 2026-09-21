#include "WarWorldEditPlacement.h"

namespace
{
    double Snap(const double Value, const double Step)
    {
        // Match browser Math.round, including negative half-grid positions.
        return FMath::FloorToDouble(Value / Step + 0.5) * Step;
    }
}

FVector WarWorldEditPlacement::SnapHorizontal(FVector Position, const double GridCentimeters)
{
    if (!FMath::IsFinite(GridCentimeters) || GridCentimeters < 0.01 || GridCentimeters > 10000 || Position.ContainsNaN()) return Position;
    Position.X = Snap(Position.X, GridCentimeters);
    Position.Y = Snap(Position.Y, GridCentimeters);
    return Position;
}

FTransform WarWorldEditPlacement::SnapTransform(const FTransform& Transform, const double GridCentimeters, const double AngleDegrees)
{
    FTransform Result = Transform;
    Result.SetLocation(SnapHorizontal(Transform.GetLocation(), GridCentimeters));
    if (FMath::IsFinite(AngleDegrees) && AngleDegrees >= 0.01 && AngleDegrees <= 360 && !Transform.ContainsNaN())
    {
        FRotator Rotation = Transform.Rotator();
        Rotation.Yaw = Snap(Rotation.Yaw, AngleDegrees);
        Result.SetRotation(Rotation.Quaternion());
    }
    return Result;
}
