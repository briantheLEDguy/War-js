#include "WarSiegeEscort.h"

namespace
{
    FVector ExpandedExtent(const FWarSiegeEscortHull& Hull,float Radius,float Half)
    {
        const FQuat Inverse=Hull.Rotation.Inverse();
        const FVector Up=Inverse.RotateVector(FVector::UpVector).GetAbs();
        FVector Padding;
        // A capsule is a vertical segment plus a sphere. Project its support
        // and the horizontal steering disk, rather than rotating a square;
        // yaw must not enlarge a round pawn's reservation.
        for (int32 Axis=0;Axis<3;++Axis)
            Padding[Axis]=Radius+Up[Axis]*(Half-Radius+20)+100*FMath::Sqrt(FMath::Max(0.,1-Up[Axis]*Up[Axis]));
        return Hull.Extent+Padding;
    }
    double Clearance(const FVector& Local,const FVector& Extent)
    {
        const FVector Gap=Local.GetAbs()-Extent;
        return FMath::Max3(Gap.X,Gap.Y,Gap.Z);
    }
    bool Intersects(const FVector& Start,const FVector& End,const FVector& Extent)
    {
        double Enter=0,Exit=1;
        for (int32 Axis=0;Axis<3;++Axis)
        {
            const double Delta=End[Axis]-Start[Axis];
            if (FMath::Abs(Delta)<1.e-9)
            { if (FMath::Abs(Start[Axis])>Extent[Axis]) return false;continue; }
            const double A=(-Extent[Axis]-Start[Axis])/Delta,B=(Extent[Axis]-Start[Axis])/Delta;
            Enter=FMath::Max(Enter,FMath::Min(A,B));Exit=FMath::Min(Exit,FMath::Max(A,B));
            if (Enter>Exit) return false;
        }
        return true;
    }
    bool MonotonicEscape(const FVector& Start,const FVector& End,const FVector& Extent)
    {
        // The maximum signed box-face distance is convex along a segment. A
        // nonnegative initial derivative therefore proves it never decreases.
        const double Gap=Clearance(Start,Extent);double Derivative=-DBL_MAX;
        for (int32 Axis=0;Axis<3;++Axis) if (FMath::Abs(FMath::Abs(Start[Axis])-Extent[Axis]-Gap)<1.e-6)
        {
            const double Delta=End[Axis]-Start[Axis];
            Derivative=FMath::Max(Derivative,FMath::Abs(Start[Axis])<1.e-9 ? FMath::Abs(Delta) : FMath::Sign(Start[Axis])*Delta);
        }
        return Derivative>=-1.e-6;
    }
    bool Valid(TConstArrayView<FWarSiegeEscortHull> Hulls,float Radius,float Half)
    {
        if (!FMath::IsFinite(Radius) || !FMath::IsFinite(Half) || Radius<=0 || Half<Radius) return false;
        for (const auto& Hull:Hulls) if (Hull.Center.ContainsNaN() || Hull.Extent.ContainsNaN()
            || Hull.Rotation.ContainsNaN() || !Hull.Rotation.IsNormalized()
            || Hull.Extent.X<=0 || Hull.Extent.Y<=0 || Hull.Extent.Z<=0) return false;
        return true;
    }
}
FVector WarSiegeEscort::Offset(int32 Seat,float Yaw)
{
    Seat=FMath::Clamp(Seat,0,17);
    const float Angle=FMath::DegreesToRadians(45.f+(Seat/2)*11.25f)*(Seat%2 ? -1 : 1);
    return FRotator(0,Yaw,0).RotateVector(FVector(FMath::Cos(Angle)*480,FMath::Sin(Angle)*480,0));
}
bool WarSiegeEscort::PointClear(const FVector& Center,TConstArrayView<FWarSiegeEscortHull> Hulls,float Radius,float Half)
{
    if (Center.ContainsNaN() || !Valid(Hulls,Radius,Half)) return false;
    for (const auto& Hull:Hulls) if (Clearance(Hull.Rotation.UnrotateVector(Center-Hull.Center),ExpandedExtent(Hull,Radius,Half))<=0) return false;
    return true;
}
bool WarSiegeEscort::PathClear(TConstArrayView<FVector> Path,TConstArrayView<FWarSiegeEscortHull> Hulls,float Radius,float Half)
{
    if (Path.IsEmpty() || !Valid(Hulls,Radius,Half)) return false;
    for (const auto& Point:Path) if (Point.ContainsNaN()) return false;
    const FVector Lift(0,0,Half+3);
    for (const auto& Hull:Hulls)
    {
        const FVector Extent=ExpandedExtent(Hull,Radius,Half);
        FVector Previous=Hull.Rotation.UnrotateVector(Path[0]+Lift-Hull.Center);
        bool Escaping=Clearance(Previous,Extent)<=0;
        for (int32 Segment=1;Segment<Path.Num();++Segment)
        {
            const FVector Next=Hull.Rotation.UnrotateVector(Path[Segment]+Lift-Hull.Center);
            if (Escaping)
            {
                if (!MonotonicEscape(Previous,Next,Extent)) return false;
                Escaping=Clearance(Next,Extent)<=0;
            }
            else if (Intersects(Previous,Next,Extent)) return false;
            Previous=Next;
        }
        if (Escaping) return false;
    }
    return true;
}
