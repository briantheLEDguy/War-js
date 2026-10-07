#include "WarZoneAnchor.h"
#include "WarCityDefinition.h"
#include "EngineUtils.h"

TArray<FName> AWarZoneAnchor::GetContentLevels() const
{
    TArray<FName> Result = ContentLevels;
    if (CityDefinition) Result.Append(CityDefinition->Packages());
    return Result;
}

bool AWarZoneAnchor::ValidateCity(FString& Error) const
{
    const bool Capital = ZoneId == TEXT("aegis_capital") || ZoneId == TEXT("riftspire_capital");
    if (!CityDefinition)
    {
        if (!Capital) return true;
        Error = TEXT("Shared city definition is missing. Restore city content and retry."); return false;
    }
    if (CityDefinition->ZoneId != ZoneId || !CityDefinition->Origin.Equals(ZoneOrigin))
    { Error = TEXT("Shared city identity or origin differs from campaign routing."); return false; }
    if (!CityDefinition->Validate(Error)) return false;
    TSet<FName> Seen;
    for (FName Package : GetContentLevels())
    {
        if (Seen.Contains(Package))
        { Error = TEXT("City scenery or gameplay is attached twice."); return false; }
        Seen.Add(Package);
    }
    return true;
}

bool AWarZoneAnchor::ContainsPoint(FVector Origin, double Extent, FVector Point)
{
    return !Origin.ContainsNaN() && !Point.ContainsNaN() && FMath::IsFinite(Extent) && Extent > 0
        && FMath::Abs(Point.X-Origin.X) <= Extent && FMath::Abs(Point.Y-Origin.Y) <= Extent;
}
AWarZoneAnchor* AWarZoneAnchor::FindAt(UWorld* World, FVector Point)
{
    if (!World) return nullptr;
    AWarZoneAnchor* Result = nullptr;
    for (TActorIterator<AWarZoneAnchor> It(World); It; ++It)
        if (It->ContainsOwnedPoint(Point))
        { if (Result) return nullptr; Result = *It; }
    return Result;
}
bool AWarZoneAnchor::ContainsOwnedPoint(FVector Point) const
{
    if (!bUseSpatialBounds) return ContainsPoint(ZoneOrigin,HalfSize,Point);
    const FVector Local = Point-ZoneOrigin;
    return !ZoneOrigin.ContainsNaN() && !Point.ContainsNaN() && !ContentMin.ContainsNaN() && !ContentMax.ContainsNaN()
        && ContentMin.X<ContentMax.X && ContentMin.Y<ContentMax.Y
        && Local.X>=ContentMin.X && Local.X<=ContentMax.X && Local.Y>=ContentMin.Y && Local.Y<=ContentMax.Y;
}
bool AWarZoneAnchor::ContainsPlayablePoint(FVector Point,double Margin) const
{
    if (!FMath::IsFinite(Margin) || Margin<0 || !ContainsOwnedPoint(Point)) return false;
    if (!bUseSpatialBounds) return ContainsPoint(ZoneOrigin,HalfSize-Margin,Point);
    if (PlayableOutline.Num()<3) return false;
    const FVector2D P(Point.X-ZoneOrigin.X,Point.Y-ZoneOrigin.Y);
    bool bInside=false;
    for (int32 I=0,J=PlayableOutline.Num()-1;I<PlayableOutline.Num();J=I++)
    {
        const auto A=PlayableOutline[J],B=PlayableOutline[I];
        if (A.ContainsNaN() || B.ContainsNaN()) return false;
        const auto D=B-A;const double L=D.SizeSquared();
        if (L<1e-12) return false;
        const auto Closest=A+D*FMath::Clamp(FVector2D::DotProduct(P-A,D)/L,0.,1.);
        const double Distance=FVector2D::Distance(P,Closest);
        if (Distance<Margin-1e-5) return false;
        if (Distance<1e-5) return Margin==0;
        if ((A.Y>P.Y)!=(B.Y>P.Y) && P.X<(B.X-A.X)*(P.Y-A.Y)/(B.Y-A.Y)+A.X) bInside=!bInside;
    }
    return bInside;
}
bool AWarZoneAnchor::ContainsPlayableSegment(FVector From,FVector To,double Margin) const
{
    if (!ContainsPlayablePoint(From,Margin) || !ContainsPlayablePoint(To,Margin)) return false;
    if (!bUseSpatialBounds) return true;
    const FVector2D A(From.X-ZoneOrigin.X,From.Y-ZoneOrigin.Y),B(To.X-ZoneOrigin.X,To.Y-ZoneOrigin.Y),D=B-A;
    TArray<double> Cuts{0,1};
    const auto Cross=[](FVector2D U,FVector2D V){return U.X*V.Y-U.Y*V.X;};
    const auto Distance=[](FVector2D P,FVector2D U,FVector2D V){
        const auto Delta=V-U;const double Length=Delta.SizeSquared();
        return FVector2D::Distance(P,U+Delta*(Length>0 ? FMath::Clamp(FVector2D::DotProduct(P-U,Delta)/Length,0.,1.) : 0));
    };
    for (int32 I=0;I<PlayableOutline.Num();I++)
    {
        const auto C=PlayableOutline[I],E=PlayableOutline[(I+1)%PlayableOutline.Num()],Edge=E-C;
        if (Margin>0 && FMath::Min3(Distance(C,A,B),Distance(A,C,E),Distance(B,C,E))<Margin-1e-5) return false;
        const double Denominator=Cross(D,Edge);
        if (FMath::Abs(Denominator)<1e-9) continue;
        const double T=Cross(C-A,Edge)/Denominator,U=Cross(C-A,D)/Denominator;
        if (T>0 && T<1 && U>=0 && U<=1) Cuts.Add(T);
    }
    Cuts.Sort();
    for (int32 I=1;I<Cuts.Num();I++)
        if (!ContainsPlayablePoint(FMath::Lerp(From,To,(Cuts[I-1]+Cuts[I])/2),Margin)) return false;
    return true;
}
AWarZoneAnchor* AWarZoneAnchor::FindById(UWorld* World, FName Id)
{
    if (!World || Id.IsNone()) return nullptr;
    AWarZoneAnchor* Result = nullptr;
    for (TActorIterator<AWarZoneAnchor> It(World); It; ++It)
        if (It->ZoneId == Id) { if (Result) return nullptr; Result = *It; }
    return Result;
}
