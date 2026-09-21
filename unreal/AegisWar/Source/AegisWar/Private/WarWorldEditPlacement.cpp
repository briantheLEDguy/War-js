#include "WarWorldEditPlacement.h"

TOptional<double> WarWorldEditPlacement::ComponentValue(const FTransform& Transform, const int32 Field)
{
    if (Field < 0 || Field > 8) return {};
    if (Field < 3) return Transform.GetLocation()[Field] / 100.0;
    if (Field >= 6) return FMath::Abs(Transform.GetScale3D()[Field - 6]);
    const auto Rotation = Transform.Rotator();
    return Field == 3 ? Rotation.Pitch : Field == 4 ? Rotation.Yaw : Rotation.Roll;
}

bool WarWorldEditPlacement::SetComponent(FTransform& Transform, const int32 Field, const double Value)
{
    if (Field < 0 || Field > 8 || !FMath::IsFinite(Value)) return false;
    if (Field < 3)
    {
        if (FMath::Abs(Value) > 1000) return false;
        FVector Position = Transform.GetLocation(); Position[Field] = Value * 100;
        Transform.SetLocation(Position);
    }
    else if (Field >= 6)
    {
        if (Value < 0.05 || Value > 20) return false;
        FVector Scale = Transform.GetScale3D();
        // Imported meshes may have mirrored axes. Editing magnitude cannot flip their basis.
        Scale[Field - 6] = FMath::Sign(Scale[Field - 6]) * Value;
        Transform.SetScale3D(Scale);
    }
    else
    {
        if (FMath::Abs(Value) > 360) return false;
        FRotator Rotation = Transform.Rotator();
        if (Field == 3) Rotation.Pitch = Value;
        else if (Field == 4) Rotation.Yaw = Value;
        else Rotation.Roll = Value;
        Transform.SetRotation(Rotation.Quaternion());
    }
    return true;
}

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

TOptional<FTransform> WarWorldEditPlacement::AtSurface(const FTransform& Basis, const FBox& LocalBounds, const FVector Surface)
{
    if (Basis.ContainsNaN() || !Basis.GetRotation().IsNormalized() || !LocalBounds.IsValid
        || LocalBounds.Min.ContainsNaN() || LocalBounds.Max.ContainsNaN() || Surface.ContainsNaN()
        || LocalBounds.GetExtent().GetMin() < 0 || LocalBounds.GetExtent().GetMax() <= 0
        || Basis.GetScale3D().GetAbs().GetMin() < 0.05 || Basis.GetScale3D().GetAbs().GetMax() > 20) return {};
    FTransform Result = Basis; Result.SetLocation(FVector::ZeroVector);
    const FBox Oriented = LocalBounds.TransformBy(Result);
    const FVector Centre = Oriented.GetCenter();
    Result.SetLocation(Surface - FVector(Centre.X, Centre.Y, Oriented.Min.Z));
    if (Result.ContainsNaN() || Result.GetLocation().GetAbsMax() > 100000) return {};
    return Result;
}

TOptional<FVector> WarWorldEditPlacement::RowStep(const FTransform& Basis, const FBox& LocalBounds, const bool bAlongY, const double Gap)
{
    if (!FMath::IsFinite(Gap) || Gap < 0 || Gap > 10000 || !AtSurface(Basis,LocalBounds,FVector::ZeroVector).IsSet()) return {};
    FVector Direction = Basis.GetRotation().RotateVector(bAlongY ? FVector::RightVector : FVector::ForwardVector);
    Direction.Z = 0;
    if (!Direction.Normalize()) return {};
    // Project the actual oriented box, rather than its larger world-axis box.
    const FVector Extent = LocalBounds.GetExtent(), Scale = Basis.GetScale3D();
    double Span = 0;
    for (int32 Axis=0; Axis<3; ++Axis)
    {
        FVector Local = FVector::ZeroVector; Local[Axis] = Extent[Axis]*Scale[Axis];
        Span += 2*FMath::Abs(FVector::DotProduct(Basis.GetRotation().RotateVector(Local),Direction));
    }
    if (Span < .01) return {};
    return Direction*(Span+Gap);
}
