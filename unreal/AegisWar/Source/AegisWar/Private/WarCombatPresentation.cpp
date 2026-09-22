#include "WarCombatPresentation.h"
#include "Animation/AnimSequence.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "ProceduralMeshComponent.h"

float WarCombatPresentation::Charge(const float Time, const float Release)
{
    if (!FMath::IsFinite(Time) || !FMath::IsFinite(Release) || Release <= 0 || Time < 0 || Time >= Release) return 0;
    return FMath::SmoothStep(0.f, Release, Time);
}

float WarCombatPresentation::Afterglow(const float Time, const float Release, const float Lifetime)
{
    if (!FMath::IsFinite(Time) || !FMath::IsFinite(Release) || !FMath::IsFinite(Lifetime)
        || Lifetime <= 0 || Time < Release) return 0;
    return 1.f-FMath::SmoothStep(Release, Release+Lifetime, Time);
}

bool WarCombatPresentation::ValidTiming(const float Duration, const float Release, const float Start, const float End)
{
    return FMath::IsFinite(Duration) && FMath::IsFinite(Release) && FMath::IsFinite(Start) && FMath::IsFinite(End)
        && Start >= 0 && Start < Release && Release < End && End < Duration && Duration <= 10;
}

AWarCombatPresentation::AWarCombatPresentation()
{
    PrimaryActorTick.bCanEverTick = true;
    Body = CreateDefaultSubobject<USkeletalMeshComponent>(TEXT("AuthoredCharacter"));
    SetRootComponent(Body);
    Body->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Body->VisibilityBasedAnimTickOption = EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
    Effects = CreateDefaultSubobject<UProceduralMeshComponent>(TEXT("ContactEffects"));
    Effects->SetupAttachment(Body);
    Effects->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Effects->SetCastShadow(false);
    // Effect triangles are intentional translucent strokes, never model stand-ins.
}

bool AWarCombatPresentation::IsCueValid() const
{
    const USkeletalMesh* Mesh = Body->GetSkeletalMeshAsset();
    return Mesh && Cue.Animation && EffectMaterial && Cue.Animation->GetSkeleton() == Mesh->GetSkeleton()
        && Body->DoesSocketExist(Cue.EmitterBone)
        && (!Cue.bWeapon || (Body->DoesSocketExist(TEXT("vfx_weapon_tip")) && Body->DoesSocketExist(TEXT("vfx_weapon_base"))))
        && WarCombatPresentation::ValidTiming(Cue.Animation->GetPlayLength(), Cue.ReleaseSeconds, Cue.TrailStart, Cue.TrailEnd);
}

void AWarCombatPresentation::BeginPlay()
{
    Super::BeginPlay();
    ReviewAtTime(0);
}

void AWarCombatPresentation::Tick(const float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    if (GetNetMode() == NM_DedicatedServer || !IsCueValid()) { Effects->ClearAllMeshSections(); return; }
    const float End = Cue.Animation->GetPlayLength()+.7f;
    const float Next = Elapsed+FMath::Clamp(DeltaSeconds,0.f,.1f);
    if (bLoopReview && Next > End) { ReviewAtTime(0); return; }
    // Bound the spacing of real evaluated samples even at a low rendering rate.
    for (float T=Elapsed; T < FMath::Min(Next,End);)
    {
        T=FMath::Min(T+1.f/120.f,FMath::Min(Next,End));
        Sample(T);
    }
    Elapsed=FMath::Min(Next,End);
    DrawEffects(Elapsed);
}

bool AWarCombatPresentation::ReviewAtTime(const float Seconds)
{
    Effects->ClearAllMeshSections();
    Trail.Reset(); bReleased=false; Elapsed=0;
    if (!IsCueValid() || !FMath::IsFinite(Seconds) || Seconds < 0 || Seconds > Cue.Animation->GetPlayLength()+.7f) return false;
    Body->PlayAnimation(Cue.Animation,false);
    Body->SetPlayRate(0);
    Effects->SetMaterial(0,EffectMaterial);
    Sample(0);
    for (float T=0; T<Seconds;)
    {
        T=FMath::Min(T+1.f/120.f,Seconds);
        Sample(T);
    }
    Elapsed=Seconds;
    DrawEffects(Seconds);
    return true;
}

void AWarCombatPresentation::Sample(const float Seconds)
{
    // Capture the exact release pose when a time step crosses the event marker.
    if (!bReleased && Seconds >= Cue.ReleaseSeconds)
    {
        Body->SetPosition(Cue.ReleaseSeconds,false);
        Body->TickAnimation(0,false);
        Body->RefreshBoneTransforms();
        ReleaseOrigin=Body->GetSocketLocation(Cue.EmitterBone);
        bReleased=true;
    }
    Body->SetPosition(FMath::Min(Seconds,Cue.Animation->GetPlayLength()),false);
    Body->TickAnimation(0,false);
    Body->RefreshBoneTransforms();
    Body->MarkRenderDynamicDataDirty();
    if (Seconds >= Cue.TrailStart && Seconds <= Cue.TrailEnd)
    {
        const FVector Tip=Body->GetSocketLocation(Cue.bWeapon ? FName(TEXT("vfx_weapon_tip")) : Cue.EmitterBone);
        const FVector Base=Cue.bWeapon ? Body->GetSocketLocation(TEXT("vfx_weapon_base")) : Tip-FVector(0,0,3);
        Trail.Add({Tip,Base,Seconds});
    }
    Trail.RemoveAll([Seconds](const FTrailSample& Point) { return Seconds-Point.Time > .16f; });
}

void AWarCombatPresentation::DrawEffects(const float Seconds)
{
    TArray<FVector> Vertices, Normals;
    TArray<int32> Indices;
    TArray<FVector2D> UV;
    TArray<FLinearColor> Colors;
    const FLinearColor Tint = Cue.Theme==EWarMagicTheme::Fire ? FLinearColor(1,.19f,.018f)
        : Cue.Theme==EWarMagicTheme::Violet ? FLinearColor(.48f,.045f,1) : FLinearColor(1,.64f,.13f);
    const FTransform Transform=Effects->GetComponentTransform();
    const auto Quad = [&](FVector A,FVector B,FVector C,FVector D,float Opacity,bool bRibbon=false)
    {
        if (Opacity <= .001f) return;
        const int32 Index=Vertices.Num();
        for (const FVector& Point : {A,B,C,D})
        {
            Vertices.Add(Transform.InverseTransformPosition(Point)); Normals.Add(FVector::UpVector);
            Colors.Add(FLinearColor(Tint.R,Tint.G,Tint.B,FMath::Clamp(Opacity,0.f,1.f)));
        }
        // Keep the soft profile continuous along adjacent trail segments.
        if (bRibbon) UV.Append({{.5f,0},{.5f,1},{.5f,1},{.5f,0}});
        else UV.Append({{0,0},{0,1},{1,1},{1,0}});
        Indices.Append({Index,Index+1,Index+2,Index,Index+2,Index+3});
    };
    const auto Stroke = [&](const FVector A,const FVector B,const float Width,const float Opacity)
    {
        FVector Side=FVector::CrossProduct(B-A,FVector::UpVector).GetSafeNormal();
        if (Side.IsNearlyZero()) Side=FVector::RightVector;
        Side*=Width;
        Quad(A-Side,A+Side,B+Side*.15f,B-Side*.15f,Opacity);
    };
    // A short tapered ribbon follows sampled hammer-head or wrist positions.
    for (int32 I=1;I<Trail.Num();++I)
    {
        const auto& A=Trail[I-1]; const auto& B=Trail[I];
        Quad(A.Base,A.Tip,B.Tip,B.Base,(1-(Seconds-B.Time)/.16f)*.7f,true);
    }
    const float Charge=WarCombatPresentation::Charge(Seconds,Cue.ReleaseSeconds);
    const float Glow=WarCombatPresentation::Afterglow(Seconds,Cue.ReleaseSeconds,.60f);
    const FVector Hand=Body->GetSocketLocation(Cue.EmitterBone);
    const FVector Forward=Body->GetComponentQuat().RotateVector(FVector(0,1,0));
    if (!Cue.bWeapon)
    {
        const float Aura=FMath::Max(Charge,Glow*.65f);
        const float Radius=Cue.Theme==EWarMagicTheme::Fire ? 10.f : 8.f;
        const FVector Across=Body->GetComponentQuat().RotateVector(FVector(1,0,0));
        // Soft crossed glow cards fill the hand silhouette without a solid orb.
        Quad(Hand-Across*Radius-FVector(0,0,Radius),Hand+Across*Radius-FVector(0,0,Radius),
            Hand+Across*Radius+FVector(0,0,Radius),Hand-Across*Radius+FVector(0,0,Radius),Aura*.5f);
        Quad(Hand-Forward*Radius-FVector(0,0,Radius),Hand+Forward*Radius-FVector(0,0,Radius),
            Hand+Forward*Radius+FVector(0,0,Radius),Hand-Forward*Radius+FVector(0,0,Radius),Aura*.35f);
        // Broken rising filaments keep a readable hand-sized source silhouette.
        for (int32 I=0;I<7;++I)
        {
            const float Phase=Seconds*2.5f+I*.8976f;
            const FVector Offset(FMath::Cos(Phase)*7,FMath::Sin(Phase)*7,2+I*1.2f);
            if (Cue.Theme==EWarMagicTheme::Fire)
            {
                const FVector Bend=Hand+Offset+FVector(0,0,8+I%3*4);
                Stroke(Hand+Offset*.35f,Bend,2.4f,Charge*.85f);
                Stroke(Bend,Bend+Across*FMath::Sin(Phase)*4+FVector(0,0,10),1.3f,Charge*.5f);
            }
            else Stroke(Hand+Offset*.45f,Hand+Offset+FVector(0,0,8),.9f,Charge*.7f);
        }
        if (Cue.Theme!=EWarMagicTheme::Fire)
        {
            // Sun-script rays are ordered; the violet study uses broken rotating crescents.
            const int32 Count=Cue.Theme==EWarMagicTheme::Gold ? 12 : 9;
            for (int32 I=0;I<Count;++I)
            {
                const float Angle=I*2*PI/Count+(Cue.Theme==EWarMagicTheme::Violet ? Seconds*1.8f : 0);
                const FVector Direction=Across*FMath::Cos(Angle)+FVector(0,0,FMath::Sin(Angle));
                Stroke(Hand+Direction*12,Hand+Direction*(I%3==0 ? 20.f : 16.f),1.2f,Charge*.7f);
            }
        }
        if (bReleased && Cue.bProjectile && Glow > 0)
        {
            const float Age=Seconds-Cue.ReleaseSeconds;
            const FVector Head=ReleaseOrigin+Forward*(Age*650.f);
            for (int32 I=0;I<5;++I)
            {
                const FVector Offset(0,FMath::Sin(I*2.4f)*3,FMath::Cos(I*2.4f)*3);
                const float Curl=Cue.Theme==EWarMagicTheme::Violet ? FMath::Sin(Age*20+I)*8 : 0;
                Stroke(Head-Forward*(36+I*7)+Offset+Across*Curl,Head+Offset,4.5f,Glow);
            }
        }
    }
    if (bReleased && Glow > 0)
    {
        const float Age=Seconds-Cue.ReleaseSeconds;
        const FVector Origin=ReleaseOrigin;
        for (int32 I=0;I<12;++I)
        {
            const float Angle=I*2.39996f;
            const FVector Velocity(FMath::Cos(Angle)*45,FMath::Sin(Angle)*45,35+(I%4)*12);
            const FVector Point=Origin+Velocity*Age-FVector(0,0,70*Age*Age);
            Stroke(Point-Velocity*.035f,Point,.8f,Glow*.65f);
        }
        if (!Cue.bProjectile && !Cue.bWeapon)
        {
            // Open gold rays and violet shards, anchored at the planted feet.
            const FVector Feet=(Body->GetSocketLocation(TEXT("foot_L"))+Body->GetSocketLocation(TEXT("foot_R")))*.5f-FVector(0,0,6);
            for (int32 I=0;I<12;++I)
            {
                const float Angle=I*PI/6;
                const FVector Radial(FMath::Cos(Angle),FMath::Sin(Angle),0);
                Stroke(Feet+Radial*(23+Age*9),Feet+Radial*(35+Age*11)+FVector(0,0,5+I%3*4),1.1f,Glow*.45f);
                if (Cue.Theme==EWarMagicTheme::Gold && I%3==0)
                    Stroke(Feet+Radial*29,Feet+Radial*29+FVector(0,0,65*(1-Age/.6f)),1.7f,Glow*.35f);
            }
        }
    }
    Effects->ClearAllMeshSections();
    if (!Vertices.IsEmpty()) Effects->CreateMeshSection_LinearColor(0,Vertices,Indices,Normals,UV,Colors,TArray<FProcMeshTangent>(),false);
}
